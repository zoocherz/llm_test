import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4
import unittest
from unittest.mock import AsyncMock, patch

TEST_DB = Path(__file__).with_name("evaluation_test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
if TEST_DB.exists():
    TEST_DB.unlink()

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from app.db.database import async_session_maker
from app.main import app
from app.models.evaluation_models import EvaluationAttempt, EvaluationDatasetItem, EvaluationRun, EvaluationRunItem
from app.models.evaluation_schemas import ExecutionPolicy, SuiteCreateRequest
from app.services.evaluation_runner import EvaluationRunner
from app.services.v1_providers import ProviderExecutionError


class EvaluationBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        if TEST_DB.exists():
            TEST_DB.unlink()

    def ready_fixture(self, modalities=None):
        suffix = uuid4().hex
        dataset = self.client.post("/api/v1/datasets", json={"name": f"fixture-{suffix}", "schema": {"modalities": modalities or ["text"]}}).json()
        version = dataset["draft_version_id"]
        self.assertEqual(self.client.post(f"/api/v1/datasets/{version}/items:commit", json=[{"external_id": "row-1", "input": {"text": "hello"}}]).status_code, 201)
        self.assertEqual(self.client.post(f"/api/v1/datasets/{version}:publish").status_code, 200)
        prompt = self.client.post("/api/v1/prompts", json={"name": f"prompt-{suffix}", "template": "{{text}}"}).json()
        pipeline = self.client.post("/api/v1/pipelines", json={"name": f"pipeline-{suffix}", "definition": {"nodes": [{"id": "generate", "kind": "generate"}], "edges": []}}).json()
        route = self.client.post("/api/v1/model-routes", json={"provider_name": "offline", "model_identifier": "deterministic", "capabilities": {"modalities": ["text"]}, "credential_ref": "env:LLM_TEST_PROVIDER_KEY"}).json()
        suite = self.client.post("/api/v1/evaluation-suites", json={"name": f"suite-{suffix}", "criteria": [{"key": "quality", "weight": 1}], "quality_threshold": 0.7}).json()
        return version, prompt, pipeline, route, suite

    def test_offline_run_snapshot_and_results(self):
        # The original baseline also guards compatibility with weighted suites.
        version, prompt, pipeline, route, suite = self.ready_fixture()
        request = {"dataset_version_id": version, "prompt_version_ids": [prompt["id"]], "candidate_route_ids": [route["id"]], "pipeline_version_id": pipeline["id"], "suite_version_id": suite["id"]}
        estimate = self.client.post("/api/v1/runs:estimate", json={key: value for key, value in request.items() if key not in {"pipeline_version_id", "suite_version_id"}})
        self.assertEqual(estimate.status_code, 200)
        self.assertEqual(estimate.json()["total_calls"], 1)
        self.assertEqual(estimate.json()["judge_calls"], 0)
        created = self.client.post("/api/v1/runs", json=request)
        self.assertEqual(created.status_code, 202)
        run_id = created.json()["id"]
        for _ in range(40):
            result = self.client.get(f"/api/v1/runs/{run_id}").json()
            if result["status"] in {"completed", "completed_with_errors"}: break
            asyncio.run(asyncio.sleep(0.02))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(created.json()["snapshot"]["suite"]["quality_threshold"], 0.7)
        self.assertNotIn("api_key", str(created.json()["snapshot"]).lower())
        self.assertEqual(created.json()["snapshot"]["routes"][0]["credential_ref"], "env:LLM_TEST_PROVIDER_KEY")
        items = self.client.get(f"/api/v1/runs/{run_id}/items").json()
        self.assertEqual(items[0]["output_json"]["text"], "[offline:{}] hello".format(route["id"][:8]))
        details = self.client.get(f"/api/v1/runs/{run_id}/details")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()[0]["results"], [])
        self.assertEqual(result['snapshot_json']['kind'], 'generation')
        self.assertGreaterEqual(details.json()[0]["attempts"][0]["latency_ms"], 1)
        self.assertEqual(details.json()[0]["dataset_item"]["external_id"], "row-1")

        secret_value = "provider-secret-must-not-leak"
        os.environ["LLM_TEST_PROVIDER_KEY"] = secret_value
        try:
            json_export = self.client.get(f"/api/v1/runs/{run_id}/export?format=json")
            self.assertEqual(json_export.status_code, 200)
            self.assertIn("attachment", json_export.headers["content-disposition"])
            self.assertEqual(json_export.json()["items"][0]["dataset_item"]["input_json"]["text"], "hello")
            self.assertNotIn(secret_value, json_export.text)
            csv_export = self.client.get(f"/api/v1/runs/{run_id}/export?format=csv")
            self.assertEqual(csv_export.status_code, 200)
            self.assertIn("external_id", csv_export.text.splitlines()[0])
            self.assertIn("row-1", csv_export.text)
            self.assertNotIn(secret_value, csv_export.text)
            self.assertEqual(self.client.get(f"/api/v1/runs/{run_id}/export?format=xml").status_code, 422)
        finally:
            os.environ.pop("LLM_TEST_PROVIDER_KEY", None)

    def test_published_dataset_is_immutable_and_preview_reports_duplicates(self):
        suffix = uuid4().hex
        dataset = self.client.post("/api/v1/datasets", json={"name": f"immutable-{suffix}"}).json()
        version = dataset["draft_version_id"]
        preview = self.client.post("/api/v1/datasets/items:preview", json=[{"external_id": "same", "input": {}}, {"external_id": "same", "input": {}}]).json()
        self.assertEqual(preview["invalid_count"], 1)
        self.assertEqual(self.client.post(f"/api/v1/datasets/{version}/items:preview", json=[{"external_id": "same", "input": {}}]).status_code, 200)
        listed = self.client.get("/api/v1/dataset-versions").json()
        self.assertTrue(any(item["id"] == version and item["dataset_name"] == f"immutable-{suffix}" for item in listed))
        self.client.post(f"/api/v1/datasets/{version}/items:commit", json=[{"external_id": "row-1", "input": {}}])
        self.client.post(f"/api/v1/datasets/{version}:publish")
        response = self.client.post(f"/api/v1/datasets/{version}/items:commit", json=[{"external_id": "row-2", "input": {}}])
        self.assertEqual(response.status_code, 409)

        revision_response = self.client.post(
            f"/api/v1/datasets/{dataset['id']}/versions",
            json={"base_version_id": version, "schema": {"modalities": ["text"]}},
        )
        self.assertEqual(revision_response.status_code, 201)
        revision = revision_response.json()
        self.assertEqual(revision["version_number"], 2)
        self.assertEqual(revision["status"], "draft")
        self.assertEqual(self.client.get(f"/api/v1/dataset-versions/{revision['id']}/items").json()["total"], 0)
        duplicate_draft = self.client.post(f"/api/v1/datasets/{dataset['id']}/versions", json={"base_version_id": version})
        self.assertEqual(duplicate_draft.status_code, 409)
        self.assertEqual(
            self.client.post(f"/api/v1/datasets/{revision['id']}/items:commit", json=[{"external_id": "row-2", "input": {"text": "replacement"}}]).status_code,
            201,
        )
        self.assertEqual(self.client.post(f"/api/v1/datasets/{revision['id']}:publish").json()["item_count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/dataset-versions/{version}/items").json()["items"][0]["external_id"], "row-1")
        self.assertEqual(self.client.get(f"/api/v1/dataset-versions/{revision['id']}/items").json()["items"][0]["external_id"], "row-2")

    def test_policy_and_suite_validation(self):
        with self.assertRaises(ValidationError):
            ExecutionPolicy(mode="benchmark", fallback_enabled=True)
        with self.assertRaises(ValidationError):
            SuiteCreateRequest(name="bad", criteria=[{"key": "quality", "weight": 0.7}], quality_threshold=0.7)

    def test_configuration_validation_and_nonpersistent_prompt_preview(self):
        before = self.client.get('/api/v1/prompts').json()
        bad = self.client.post('/api/v1/prompts', json={'name': 'bad syntax', 'template': 'Line one\n{{text | trim}}'})
        self.assertEqual(bad.status_code, 422)
        self.assertIn('строка 2', bad.json()['detail'][0]['msg'])
        self.assertEqual(self.client.post('/api/v1/prompts', json={'name': 'empty', 'template': '   '}).status_code, 422)
        with patch('app.services.evaluation_runner.generate_external', new_callable=AsyncMock) as provider:
            preview = self.client.post('/api/v1/prompts:preview', json={'template': 'Summary: {{input.text}} / {{customer.name}}', 'input': {'text': 'hello', 'customer': {'name': 'sample'}}})
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.json()['rendered'], 'Summary: hello / sample')
            provider.assert_not_awaited()
        self.assertEqual(self.client.get('/api/v1/prompts').json(), before)
        missing = self.client.post('/api/v1/prompts:preview', json={'template': '{{missing}}', 'input': {'text': 'private-sample'}})
        self.assertEqual(missing.status_code, 422)
        self.assertNotIn('private-sample', missing.text)
        for definition in [{'type': 'object', 'properties': {}}, {'nodes': [{'id': 'a', 'kind': 'generate'}, {'id': 'b', 'kind': 'generate'}]}, {'nodes': ['generate']}, {'nodes': [{'id': 'a', 'kind': 'generate'}], 'edges': 'wrong'}]:
            result = self.client.post('/api/v1/pipelines', json={'name': 'unsupported', 'definition': definition})
            self.assertEqual(result.status_code, 422)
            self.assertIn('не схема ответа', result.json()['detail'][0]['msg'])

    def wait_run(self, run_id):
        import time
        for _ in range(200):
            run = self.client.get(f'/api/v1/runs/{run_id}').json()
            if run['status'] in {'completed', 'completed_with_errors', 'failed', 'cancelled'}:
                return run
            time.sleep(0.02)
        self.fail('Run did not finish')

    def test_rendered_prompt_and_missing_variable_preflight(self):
        version, prompt, pipeline, route, suite = self.ready_fixture()
        custom = self.client.post('/api/v1/prompts', json={'name': 'rendered', 'template': 'Summarize: {{text}}'}).json()
        request = {'dataset_version_id': version, 'prompt_version_ids': [custom['id']], 'candidate_route_ids': [route['id']], 'pipeline_version_id': pipeline['id'], 'suite_version_id': suite['id']}
        request.pop('suite_version_id')  # Generation must not require evaluation rules.
        created = self.client.post('/api/v1/runs', json=request)
        self.assertEqual(created.status_code, 202)
        self.wait_run(created.json()['id'])
        details = self.client.get('/api/v1/runs/' + created.json()['id'] + '/details').json()
        self.assertTrue(details[0]['output_json']['text'].endswith('Summarize: hello'))
        self.client.put('/api/v1/model-routes/' + route['id'], json={'provider_name': 'google', 'model_identifier': 'test-model', 'credential_ref': 'env:UNIT_TEST_JUDGE_KEY'})
        with patch('app.services.evaluation_runner.generate_external', new_callable=AsyncMock, return_value={'text': 'summary'}) as provider:
            remote = self.client.post('/api/v1/runs', json=request)
            self.assertEqual(remote.status_code, 202)
            self.assertEqual(self.wait_run(remote.json()['id'])['status'], 'completed')
            provider.assert_awaited_once()
            self.assertEqual(provider.call_args.args[1].prompt, 'Summarize: hello')
        bad = self.client.post('/api/v1/prompts', json={'name': 'missing', 'template': '{{absent}}'}).json()
        request['prompt_version_ids'] = [bad['id']]
        with patch('app.services.evaluation_runner.generate_external', new_callable=AsyncMock) as provider:
            rejected = self.client.post('/api/v1/runs', json=request)
            self.assertEqual(rejected.status_code, 422)
            self.assertIn('absent', rejected.json()['detail'])
            provider.assert_not_awaited()

    def test_separate_judge_uses_saved_answers_and_preserves_prior_evaluations(self):
        version, prompt, pipeline, route, suite = self.ready_fixture()
        request = {'dataset_version_id': version, 'prompt_version_ids': [prompt['id']], 'candidate_route_ids': [route['id']], 'pipeline_version_id': pipeline['id'], 'suite_version_id': suite['id']}
        source_id = self.client.post('/api/v1/runs', json=request).json()['id']
        self.wait_run(source_id)
        original = self.client.get(f'/api/v1/runs/{source_id}/details').json()
        judge_prompt = self.client.post('/api/v1/prompts', json={'name': 'judge', 'template': 'Input: {{input}} Reference: {{reference}} Output: {{output}}'}).json()
        judge = self.client.post('/api/v1/model-routes', json={'provider_name': 'openrouter', 'model_identifier': 'test-judge', 'credential_ref': 'env:UNIT_TEST_JUDGE_KEY'}).json()
        assessment = {'judge_route_id': judge['id'], 'judge_prompt_id': judge_prompt['id'], 'suite_version_id': suite['id']}
        with patch.dict(os.environ, {'UNIT_TEST_JUDGE_KEY': 'not-a-real-key'}):
            with patch('app.services.evaluation_runner.generate_external', new_callable=AsyncMock, return_value={'text': '{"scores":{"quality":0.75},"rationale":"Matches reference"}'}) as provider:
                first = self.client.post(f'/api/v1/runs/{source_id}/evaluations', json=assessment)
                self.assertEqual(first.status_code, 202, first.text)
                first_id = first.json()['id']
                self.assertEqual(self.wait_run(first_id)['status'], 'completed')
                provider.assert_awaited_once()
                self.assertEqual(provider.call_args.args[0]['id'], judge['id'])
                self.assertIn(original[0]['output_json']['text'], provider.call_args.args[1].prompt)
            first_details = self.client.get(f'/api/v1/runs/{first_id}/details').json()
            self.assertEqual(first_details[0]['results'][0]['numeric_score'], 0.75)
            self.assertEqual(first_details[0]['evaluation_source']['source_item_id'], original[0]['id'])
            with patch('app.services.evaluation_runner.generate_external', new_callable=AsyncMock, return_value={'text': '{"scores":{"quality":99},"rationale":"invalid scale"}'}) as provider:
                second = self.client.post(f'/api/v1/runs/{source_id}/evaluations', json=assessment)
                self.assertEqual(second.status_code, 202)
                second_id = second.json()['id']
                self.assertNotEqual(first_id, second_id)
                self.assertEqual(self.wait_run(second_id)['status'], 'completed_with_errors')
                provider.assert_awaited_once()
        failed = self.client.get(f'/api/v1/runs/{second_id}/details').json()[0]
        self.assertIsNone(failed['results'][0]['numeric_score'])
        self.assertEqual(failed['error_json']['code'], 'invalid_judge_response')
        self.assertEqual(self.client.get(f'/api/v1/runs/{source_id}/details').json(), original)
        self.assertEqual(self.client.get(f'/api/v1/runs/{first_id}/details').json(), first_details)
        history = self.client.get(f'/api/v1/runs/{source_id}/evaluations').json()
        self.assertEqual({entry['id'] for entry in history}, {first_id, second_id})
        exported = self.client.get(f'/api/v1/runs/{first_id}/export?format=json')
        self.assertEqual(exported.status_code, 200)
        self.assertNotIn('not-a-real-key', exported.text)
        self.assertEqual(self.client.post(f'/api/v1/runs/{first_id}/evaluations', json=assessment).status_code, 409)
        self.assertEqual(self.client.delete('/api/v1/model-routes/' + judge['id']).status_code, 204)
        saved = self.client.get(f'/api/v1/runs/{first_id}').json()['snapshot_json']
        self.assertEqual(saved['judge']['route']['model_identifier'], 'test-judge')

    def test_incompatible_route_is_rejected_before_run(self):
        version, prompt, pipeline, route, suite = self.ready_fixture(modalities=["text", "image"])
        request = {"dataset_version_id": version, "prompt_version_ids": [prompt["id"]], "candidate_route_ids": [route["id"]], "pipeline_version_id": pipeline["id"], "suite_version_id": suite["id"]}
        response = self.client.post("/api/v1/runs", json=request)
        self.assertEqual(response.status_code, 422)
        self.assertIn("capability", response.json()["detail"].lower())

    def test_plain_text_reference_mapping(self):
        from app.api.evaluation import apply_import_mapping
        from app.models.evaluation_schemas import DatasetImportMapping
        mapping = DatasetImportMapping(external_id_field='id', input_text_field='body', reference_field='answer', reference_format='text')
        self.assertEqual(apply_import_mapping({'id': '1', 'body': 'input', 'answer': 'plain text'}, mapping)['reference'], {'text': 'plain text'})
        self.assertEqual(apply_import_mapping({'id': '1', 'body': 'input', 'answer': ''}, mapping)['reference'], {})
        mapping.reference_format = 'json'
        with self.assertRaises(ValueError):
            apply_import_mapping({'id': '1', 'body': 'input', 'answer': 'plain text'}, mapping)
        self.assertEqual(apply_import_mapping({'id': '1', 'body': 'input', 'answer': '{"text":"value"}'}, mapping)['reference'], {'text': 'value'})

    def test_retry_subset_empty_response_and_history(self):
        async def seed():
            async with async_session_maker() as db:
                route_id, prompt_id = str(uuid4()), str(uuid4())
                sources = [EvaluationDatasetItem(dataset_version_id=str(uuid4()), external_id=str(i), input_json={'text': 'test'}) for i in range(2)]
                snapshot = {'kind': 'generation', 'routes': [{'id': route_id, 'provider_name': 'openrouter', 'model_identifier': 'test'}], 'prompts': [{'id': prompt_id, 'template': '{{text}}'}]}
                run = EvaluationRun(snapshot_json=snapshot)
                db.add_all([*sources, run]); await db.flush()
                db.add_all([EvaluationRunItem(run_id=run.id, dataset_item_id=s.id, prompt_version_id=prompt_id, route_id=route_id) for s in sources])
                await db.commit()
                return run.id, snapshot
        async def execute(run_id):
            async with async_session_maker() as db:
                await EvaluationRunner(db).execute(run_id)
        run_id, snapshot = asyncio.run(seed())
        with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(side_effect=[{'text': '  '}, {'text': 'keep'}])) as provider:
            asyncio.run(execute(run_id))
            self.assertEqual(provider.await_count, 2)
        before = self.client.get(f'/api/v1/runs/{run_id}/details').json()
        failed = next(row for row in before if row['status'] == 'failed')
        kept = next(row for row in before if row['status'] == 'completed')
        self.assertEqual(failed['error_json']['code'], 'empty_response')
        self.assertEqual(self.client.post(f'/api/v1/runs/{run_id}:retry', json={'item_ids': [str(uuid4())]}).status_code, 422)
        with patch('app.api.evaluation.execute_background', new=AsyncMock()):
            response = self.client.post(f'/api/v1/runs/{run_id}:retry', json={'item_ids': [failed['id'], failed['id']]})
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()['retry_calls'], 1)
            self.assertEqual(self.client.post(f'/api/v1/runs/{run_id}:retry', json={'item_ids': [failed['id']]}).status_code, 409)
        with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(return_value={'text': 'retried'})) as provider:
            asyncio.run(execute(run_id))
            self.assertEqual(provider.await_count, 1)
        after = self.client.get(f'/api/v1/runs/{run_id}/details').json()
        self.assertEqual(next(row for row in after if row['id'] == kept['id']), kept)
        retried = next(row for row in after if row['id'] == failed['id'])
        self.assertEqual(retried['output_json']['text'], 'retried')
        self.assertIsNone(retried['error_json'])
        self.assertEqual([a['kind'] for a in retried['attempts']], ['initial', 'retry'])
        state = self.client.get(f'/api/v1/runs/{run_id}').json()
        self.assertEqual(state['snapshot_json'], snapshot)
        self.assertEqual(state['progress_json'], {'completed': 2, 'total': 2, 'failed': 0})

    def test_independent_suite_and_judge_retry(self):
        version, prompt, pipeline, route, _ = self.ready_fixture()
        suite = self.client.post('/api/v1/evaluation-suites', json={'name': 'independent', 'scoring_mode': 'independent', 'criteria': [{'key': 'accuracy', 'min_score': 0, 'max_score': 5}, {'key': 'style', 'min_score': 0, 'max_score': 10}]}).json()
        self.assertEqual(suite['scoring_mode'], 'independent')
        self.assertEqual(self.client.post('/api/v1/evaluation-suites', json={'name': 'bad', 'scoring_mode': 'independent', 'criteria': [{'key': 'x', 'min_score': 5, 'max_score': 5}]}).status_code, 422)
        source = self.client.post('/api/v1/runs', json={'dataset_version_id': version, 'prompt_version_ids': [prompt['id']], 'candidate_route_ids': [route['id']], 'pipeline_version_id': pipeline['id']}).json()
        def wait(run_id):
            for _ in range(100):
                result = self.client.get(f'/api/v1/runs/{run_id}').json()
                if result['status'] in {'completed', 'completed_with_errors'}: return result
                asyncio.run(asyncio.sleep(0.02))
            self.fail('Run did not finish')
        wait(source['id'])
        judge = self.client.post('/api/v1/prompts', json={'name': 'judge-independent', 'template': '{{output}}'}).json()
        assessed = self.client.post(f"/api/v1/runs/{source['id']}/evaluations", json={'judge_route_id': route['id'], 'judge_prompt_id': judge['id'], 'suite_version_id': suite['id']}).json()
        wait(assessed['id'])
        details = self.client.get(f"/api/v1/runs/{assessed['id']}/details").json()
        self.assertEqual(details[0]['results'][0]['value_json']['scores'], {'accuracy': 5, 'style': 10})
        self.assertIsNone(details[0]['results'][0]['numeric_score'])
        self.assertEqual(self.client.post(f"/api/v1/runs/{assessed['id']}:retry", json={'item_ids': [details[0]['id']]}).status_code, 202)
        wait(assessed['id'])
        latest = self.client.get(f"/api/v1/runs/{assessed['id']}/details").json()[0]
        self.assertEqual(len(latest['result_history']), 2)
        self.assertEqual(len(latest['results']), 1)
        self.assertEqual(latest['results'][0]['value_json']['_attempt'], 2)
        self.assertIn('criteria_scores', self.client.get(f"/api/v1/runs/{assessed['id']}/export?format=csv").text)

    def test_cancel_running_preserves_current_answer_and_stops_remaining(self):
        async def exercise():
            async with async_session_maker() as db:
                route_id, prompt_id = str(uuid4()), str(uuid4())
                source = EvaluationDatasetItem(dataset_version_id=str(uuid4()), external_id='cancel-source', input_json={'text': 'test'})
                run = EvaluationRun(snapshot_json={'kind': 'generation', 'routes': [{'id': route_id, 'provider_name': 'google', 'model_identifier': 'test'}], 'prompts': [{'id': prompt_id, 'template': '{{text}}'}]})
                db.add_all([source, run]); await db.flush()
                db.add_all([EvaluationRunItem(run_id=run.id, dataset_item_id=source.id, prompt_version_id=prompt_id, route_id=route_id) for _ in range(2)])
                await db.commit()
                run_id = run.id
            async def finish_current(*args, **kwargs):
                await kwargs['on_attempt'](1)
                live = (await asyncio.to_thread(self.client.get, f'/api/v1/runs/{run_id}')).json()
                details = (await asyncio.to_thread(self.client.get, f'/api/v1/runs/{run_id}/details')).json()
                active = next(row for row in details if row['status'] == 'running')
                self.assertEqual(live['progress_json']['active_item_id'], active['id'])
                self.assertEqual(live['progress_json']['http_attempt'], 1)
                self.assertEqual(active['attempts'][0]['route_snapshot_json']['http_attempts'], 1)
                self.assertIsNone(active['attempts'][0]['latency_ms'])
                response = await asyncio.to_thread(self.client.post, f'/api/v1/runs/{run_id}:cancel')
                self.assertEqual(response.json()['status'], 'cancelling')
                retry = await asyncio.to_thread(self.client.post, f'/api/v1/runs/{run_id}:retry', json={'item_ids': [str(uuid4())]})
                self.assertEqual(retry.status_code, 409)
                return {'text': 'current answer preserved', 'finish_reason': 'STOP'}
            with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(side_effect=finish_current)) as provider:
                async with async_session_maker() as db:
                    await EvaluationRunner(db).execute(run_id)
                self.assertEqual(provider.await_count, 1)
            return run_id
        run_id = asyncio.run(exercise())
        state = self.client.get(f'/api/v1/runs/{run_id}').json()
        self.assertEqual(state['status'], 'cancelled')
        rows = self.client.get(f'/api/v1/runs/{run_id}/details').json()
        self.assertEqual(sorted(r['status'] for r in rows), ['cancelled', 'completed'])
        remaining = next(r for r in rows if r['status'] == 'cancelled')
        with patch('app.api.evaluation.execute_background', new=AsyncMock()):
            self.assertEqual(self.client.post(f'/api/v1/runs/{run_id}:retry', json={'item_ids': [remaining['id']]}).status_code, 202)
        self.assertEqual(self.client.post(f'/api/v1/runs/{run_id}:cancel').json()['status'], 'cancelled')

    def test_truncated_response_is_failed_and_retained_in_attempt(self):
        async def exercise():
            async with async_session_maker() as db:
                route_id, prompt_id = str(uuid4()), str(uuid4())
                source = EvaluationDatasetItem(dataset_version_id=str(uuid4()), external_id='truncated', input_json={'text': 'test'})
                run = EvaluationRun(snapshot_json={'kind': 'generation', 'routes': [{'id': route_id, 'provider_name': 'google', 'model_identifier': 'test'}], 'prompts': [{'id': prompt_id, 'template': '{{text}}'}], 'policy': {'max_output_tokens': 8192}})
                db.add_all([source, run]); await db.flush()
                db.add(EvaluationRunItem(run_id=run.id, dataset_item_id=source.id, prompt_version_id=prompt_id, route_id=route_id)); await db.commit()
                run_id = run.id
            with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(return_value={'text': 'partial', 'finish_reason': 'MAX_TOKENS'})) as provider:
                async with async_session_maker() as db:
                    await EvaluationRunner(db).execute(run_id)
                self.assertEqual(provider.call_args.args[1].max_output_tokens, 8192)
            return run_id
        row = self.client.get(f'/api/v1/runs/{asyncio.run(exercise())}/details').json()[0]
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['error_json']['code'], 'truncated_response')
        self.assertEqual(row['attempts'][0]['output_json']['text'], 'partial')

    def test_cancel_and_item_failure_terminal_status(self):
        async def make_cancelled_run():
            async with async_session_maker() as db:
                run = EvaluationRun(snapshot_json={"suite": {"criteria": [], "quality_threshold": 0}}, progress_json={})
                db.add(run); await db.commit()
                return run.id
        run_id = asyncio.run(make_cancelled_run())
        self.assertEqual(self.client.post(f"/api/v1/runs/{run_id}:cancel").json()["status"], "cancelled")

        async def execute_broken_run():
            async with async_session_maker() as db:
                run = EvaluationRun(snapshot_json={"suite": {"criteria": [{"key": "quality", "weight": 1}], "quality_threshold": 0.5}}, progress_json={})
                db.add(run); await db.flush()
                db.add(EvaluationRunItem(run_id=run.id, dataset_item_id=str(uuid4()), prompt_version_id=str(uuid4()), route_id=str(uuid4())))
                await db.commit(); run_id = run.id
            async with async_session_maker() as db:
                await EvaluationRunner(db).execute(run_id)
                return (await db.get(EvaluationRun, run_id)).status
        self.assertEqual(asyncio.run(execute_broken_run()), "completed_with_errors")


    def test_provider_failure_keeps_structured_error_and_attempt(self):
        async def execute_provider_failure():
            route_id = str(uuid4())
            async with async_session_maker() as db:
                source = EvaluationDatasetItem(dataset_version_id=str(uuid4()), external_id="provider-error", input_json={"text": "hello"})
                run = EvaluationRun(snapshot_json={"routes": [{"id": route_id, "provider_name": "openrouter", "model_identifier": "model", "credential_ref": "env:KEY", "timeout_seconds": 1}], "suite": {"criteria": [], "quality_threshold": 0}}, progress_json={})
                db.add_all([source, run]); await db.flush()
                item = EvaluationRunItem(run_id=run.id, dataset_item_id=source.id, prompt_version_id=str(uuid4()), route_id=route_id)
                db.add(item); await db.commit(); run_id, item_id = run.id, item.id
            failure = ProviderExecutionError("http_402", "Provider returned an HTTP error", False)
            with patch("app.services.evaluation_runner.generate_external", new=AsyncMock(side_effect=failure)):
                async with async_session_maker() as db:
                    await EvaluationRunner(db).execute(run_id)
            async with async_session_maker() as db:
                item = await db.get(EvaluationRunItem, item_id)
                attempt = (await db.execute(select(EvaluationAttempt).where(EvaluationAttempt.run_item_id == item_id))).scalar_one()
                return item.error_json, attempt.error_json

        item_error, attempt_error = asyncio.run(execute_provider_failure())
        expected = {"code": "http_402", "message": "Provider returned an HTTP error", "retryable": False}
        self.assertEqual(item_error, expected)
        self.assertEqual(attempt_error, expected)

    def test_model_route_can_be_updated_and_deleted(self):
        created = self.client.post("/api/v1/model-routes", json={"provider_name": "openrouter", "model_identifier": "old/model", "capabilities": {"modalities": ["text"]}, "credential_ref": "env:LLM_TEST_PROVIDER_KEY", "timeout_seconds": 60})
        self.assertEqual(created.status_code, 201)
        route_id = created.json()["id"]
        updated = self.client.put(f"/api/v1/model-routes/{route_id}", json={"provider_name": "openrouter", "model_identifier": "openrouter/free", "capabilities": {"modalities": ["text"]}, "credential_ref": "env:LLM_TEST_PROVIDER_KEY", "timeout_seconds": 30})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["model_identifier"], "openrouter/free")
        self.assertEqual(updated.json()["timeout_seconds"], 30)
        self.assertIn(route_id, [item["id"] for item in self.client.get("/api/v1/model-routes").json()])
        self.assertEqual(self.client.delete(f"/api/v1/model-routes/{route_id}").status_code, 204)
        self.assertNotIn(route_id, [item["id"] for item in self.client.get("/api/v1/model-routes").json()])
        self.assertEqual(self.client.delete(f"/api/v1/model-routes/{route_id}").status_code, 404)

    def test_csv_and_jsonl_import_preview_then_explicit_commit(self):
        version_count_before_preview = len(self.client.get("/api/v1/dataset-versions").json())
        csv_content = (
            'external_id,input,reference,metadata,tags\r\n'
            'csv-1,"{""text"": ""hello""}","{""answer"": ""ok""}","{""language"": ""ru""}","[""gold""]"\r\n'
            'csv-2,"{""text"": ""world""}",,,\r\n'
        ).encode("utf-8")
        preview = self.client.post("/api/v1/datasets/import:preview", files={"file": ("items.csv", csv_content, "text/csv")})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["source_format"], "csv")
        self.assertEqual(preview.json()["valid_count"], 2)
        self.assertEqual(preview.json()["preview"][0]["metadata"], {"language": "ru"})

        invalid_jsonl = b'{"external_id":"json-1","input":{"text":"ok"}}\nnot-json\n'
        invalid = self.client.post("/api/v1/datasets/import:preview", files={"file": ("items.jsonl", invalid_jsonl, "application/x-ndjson")})
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.json()["invalid_count"], 1)
        self.assertEqual(invalid.json()["row_errors"][0]["row"], 2)
        self.assertIn("invalid JSON", invalid.json()["row_errors"][0]["reason"])

        noncanonical_csv = 'id,transcript,reference_summary\r\n1,hello,"{""summary"":""ok""}"\r\n'.encode("utf-8")
        noncanonical_csv_preview = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("legacy.csv", noncanonical_csv, "text/csv")},
        )
        self.assertEqual(noncanonical_csv_preview.status_code, 200)
        self.assertEqual(noncanonical_csv_preview.json()["invalid_count"], 1)
        self.assertEqual(noncanonical_csv_preview.json()["source_fields"], ["id", "reference_summary", "transcript"])
        csv_mapping = {"external_id_field": "id", "input_text_field": "transcript", "reference_field": "reference_summary"}
        mapped_csv_preview = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("legacy.csv", noncanonical_csv, "text/csv")},
            data={"mapping_json": json.dumps(csv_mapping)},
        )
        self.assertEqual(mapped_csv_preview.status_code, 200)
        self.assertEqual(mapped_csv_preview.json()["valid_count"], 1)
        self.assertEqual(mapped_csv_preview.json()["preview"][0]["reference"], {"summary": "ok"})

        cp1251_csv = "id;transcript\r\n1;Привет из CSV\r\n".encode("cp1251")
        cp1251_preview = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("windows.csv", cp1251_csv, "text/csv")},
        )
        self.assertEqual(cp1251_preview.status_code, 200)
        self.assertEqual(cp1251_preview.json()["source_encoding"], "windows-1251")
        self.assertEqual(cp1251_preview.json()["source_delimiter"], ";")
        self.assertEqual(cp1251_preview.json()["source_preview"][0]["values"]["transcript"], "Привет из CSV")
        cp1251_mapping = {"external_id_field": "id", "input_text_field": "transcript", "reference_field": None}
        cp1251_mapped = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("windows.csv", cp1251_csv, "text/csv")},
            data={"mapping_json": json.dumps(cp1251_mapping)},
        )
        self.assertEqual(cp1251_mapped.json()["valid_count"], 1)

        pipe_csv = b"id|transcript\n1|pipe text\n"
        pipe_preview = self.client.post("/api/v1/datasets/import:preview", files={"file": ("pipe.csv", pipe_csv, "text/csv")})
        self.assertEqual(pipe_preview.json()["source_delimiter"], "|")
        self.assertEqual(pipe_preview.json()["source_fields"], ["id", "transcript"])

        noncanonical = (json.dumps({"id": 1, "transcript": "hello", "reference_summary": json.dumps({"summary": "ok"})}) + "\n").encode("utf-8")
        noncanonical_preview = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("legacy.jsonl", noncanonical, "application/x-ndjson")},
        )
        self.assertEqual(noncanonical_preview.status_code, 200)
        reason = noncanonical_preview.json()["row_errors"][0]["reason"]
        self.assertIn("external_id", reason)
        self.assertIn("input", reason)
        self.assertIn("id, transcript, reference_summary", reason)
        self.assertEqual(noncanonical_preview.json()["source_preview"][0]["values"]["transcript"], "hello")
        mapping = {"external_id_field": "id", "input_text_field": "transcript", "reference_field": "reference_summary"}
        mapped_preview = self.client.post(
            "/api/v1/datasets/import:preview",
            files={"file": ("legacy.jsonl", noncanonical, "application/x-ndjson")},
            data={"mapping_json": json.dumps(mapping)},
        )
        self.assertEqual(mapped_preview.status_code, 200)
        self.assertEqual(mapped_preview.json()["valid_count"], 1)
        self.assertTrue(mapped_preview.json()["mapping_applied"])
        self.assertEqual(mapped_preview.json()["preview"][0]["external_id"], "1")
        self.assertEqual(mapped_preview.json()["preview"][0]["input"], {"text": "hello"})
        self.assertEqual(mapped_preview.json()["preview"][0]["reference"], {"summary": "ok"})
        manual_preview = self.client.post("/api/v1/datasets/items:preview", json=[{"id": "legacy", "transcript": "hello"}])
        self.assertEqual(manual_preview.status_code, 200)
        self.assertEqual(manual_preview.json()["invalid_count"], 1)
        self.assertIn("input", manual_preview.json()["row_errors"][0]["reason"])
        self.assertEqual(len(self.client.get("/api/v1/dataset-versions").json()), version_count_before_preview)

        suffix = uuid4().hex
        mapped_dataset = self.client.post("/api/v1/datasets", json={"name": f"mapped-import-{suffix}", "schema": {"modalities": ["text"]}}).json()
        mapped_commit = self.client.post(
            f"/api/v1/datasets/{mapped_dataset['draft_version_id']}/items:import",
            files={"file": ("legacy.jsonl", noncanonical, "application/x-ndjson")},
            data={"mapping_json": json.dumps(mapping)},
        )
        self.assertEqual(mapped_commit.status_code, 201)
        mapped_version = next(item for item in self.client.get("/api/v1/dataset-versions").json() if item["id"] == mapped_dataset["draft_version_id"])
        self.assertEqual(mapped_version["schema_json"]["import_mapping"], mapping)
        self.assertEqual(mapped_version["schema_json"]["import_source"], {"format": "jsonl", "encoding": "utf-8", "delimiter": None})
        mapped_items = self.client.get(f"/api/v1/dataset-versions/{mapped_dataset['draft_version_id']}/items").json()["items"]
        self.assertEqual(mapped_items[0]["reference_json"], {"summary": "ok"})

        csv_dataset = self.client.post("/api/v1/datasets", json={"name": f"csv-import-{suffix}"}).json()
        rejected = self.client.post(
            f"/api/v1/datasets/{csv_dataset['draft_version_id']}/items:import",
            files={"file": ("items.jsonl", invalid_jsonl, "application/x-ndjson")},
        )
        self.assertEqual(rejected.status_code, 422)
        committed = self.client.post(
            f"/api/v1/datasets/{csv_dataset['draft_version_id']}/items:import",
            files={"file": ("items.csv", csv_content, "text/csv")},
        )
        self.assertEqual(committed.status_code, 201)
        self.assertEqual(committed.json()["committed_count"], 2)
        self.assertEqual(self.client.post(f"/api/v1/datasets/{csv_dataset['draft_version_id']}:publish").json()["item_count"], 2)

        jsonl_dataset = self.client.post("/api/v1/datasets", json={"name": f"jsonl-import-{suffix}"}).json()
        valid_jsonl = b'{"external_id":"json-1","input":{"text":"from jsonl"},"tags":["sample"]}\n'
        jsonl_commit = self.client.post(
            f"/api/v1/datasets/{jsonl_dataset['draft_version_id']}/items:import",
            files={"file": ("items.jsonl", valid_jsonl, "application/x-ndjson")},
        )
        self.assertEqual(jsonl_commit.status_code, 201)
        self.assertEqual(jsonl_commit.json()["source_format"], "jsonl")
        self.assertEqual(self.client.post(f"/api/v1/datasets/{jsonl_dataset['draft_version_id']}:publish").json()["item_count"], 1)
        listed_items = self.client.get(f"/api/v1/dataset-versions/{jsonl_dataset['draft_version_id']}/items")
        self.assertEqual(listed_items.status_code, 200)
        self.assertEqual(listed_items.json()["total"], 1)
        self.assertEqual(listed_items.json()["items"][0]["input_json"], {"text": "from jsonl"})

    def test_legacy_test_runs_static_route_is_not_captured_as_task_id(self):
        response = self.client.get("/api/tasks/runs?limit=100")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_crt_endpoint_snapshot_edit_and_legacy_preflight(self):
        version, prompt, pipeline, route, suite = self.ready_fixture()
        rejected_secret = self.client.post('/api/v1/model-routes', json={'provider_name': 'crt_mko', 'model_identifier': 'test', 'capabilities': {'base_url': 'https://user:synthetic-private-secret@mko.test/api/v1'}})
        self.assertEqual(rejected_secret.status_code, 422)
        self.assertNotIn('synthetic-private-secret', rejected_secret.text)
        configuration = {'provider_name': 'crt_mko', 'model_identifier': 'synthetic', 'capabilities': {'modalities': ['text'], 'base_url': 'https://first.test:9443/api/v1'}, 'timeout_seconds': 180}
        saved = self.client.put('/api/v1/model-routes/' + route['id'], json=configuration)
        self.assertEqual(saved.status_code, 200)
        request = {'dataset_version_id': version, 'prompt_version_ids': [prompt['id']], 'candidate_route_ids': [route['id']], 'pipeline_version_id': pipeline['id']}
        with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(return_value={'text': 'final'})) as provider:
            created = self.client.post('/api/v1/runs', json=request)
            self.assertEqual(created.status_code, 202)
            run_id = created.json()['id']
            state = self.wait_run(run_id)
            self.assertEqual(provider.call_args.args[0]['capabilities_json']['base_url'], 'https://first.test:9443/api/v1')
        configuration['capabilities']['base_url'] = 'https://second.test/api/v1'
        self.assertEqual(self.client.put('/api/v1/model-routes/' + route['id'], json=configuration).status_code, 200)
        snapshot = self.client.get('/api/v1/runs/' + run_id).json()['snapshot_json']
        self.assertEqual(snapshot, state['snapshot_json'])
        rows = self.client.get('/api/v1/runs/' + run_id + '/details').json()
        with patch('app.services.evaluation_runner.generate_external', new=AsyncMock(return_value={'text': 'repeat'})) as provider:
            self.assertEqual(self.client.post('/api/v1/runs/' + run_id + ':retry', json={'item_ids': [rows[0]['id']]}).status_code, 202)
            self.wait_run(run_id)
            self.assertEqual(provider.call_args.args[0]['capabilities_json']['base_url'], 'https://first.test:9443/api/v1')
        async def legacy_snapshot():
            async with async_session_maker() as db:
                run = await db.get(EvaluationRun, run_id)
                snapshot = dict(run.snapshot_json)
                snapshot['routes'][0]['capabilities_json'].pop('base_url')
                run.snapshot_json = snapshot
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(run, 'snapshot_json')
                await db.commit()
        asyncio.run(legacy_snapshot())
        with patch('app.services.evaluation_runner.generate_external', new=AsyncMock()) as provider:
            rejected = self.client.post('/api/v1/runs/' + run_id + ':retry', json={'item_ids': [rows[0]['id']]})
            self.assertEqual(rejected.status_code, 422)
            self.assertEqual(rejected.json()['detail']['code'], 'endpoint_required')
            provider.assert_not_called()
        self.assertEqual(self.client.get('/api/v1/runs/' + run_id).json()['status'], 'completed')

if __name__ == "__main__":
    unittest.main()
