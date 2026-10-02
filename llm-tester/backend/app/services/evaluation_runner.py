import json
from datetime import datetime
from time import perf_counter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.evaluation_models import EvaluationAttempt, EvaluationDatasetItem, EvaluationResult, EvaluationRun, EvaluationRunItem
from app.services.prompt_rendering import render_prompt
from app.services.judge_evaluation import judge_prompt, parse_judgment
from app.services.v1_providers import NormalizedGenerationRequest, ProviderExecutionError, generate_external


class EvaluationRunner:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute(self, run_id: str, item_ids: set[str] | None = None) -> None:
        run = await self.db.get(EvaluationRun, run_id)
        if not run or run.status != 'queued':
            return
        claimed = await self.db.execute(update(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.status == 'queued').values(status='running', started_at=run.started_at or datetime.utcnow()).execution_options(synchronize_session=False))
        if claimed.rowcount != 1:
            await self.db.rollback()
            return
        await self.db.commit()
        await self.db.refresh(run)
        items = (await self.db.execute(select(EvaluationRunItem).where(EvaluationRunItem.run_id == run_id))).scalars().all()
        snapshot = run.snapshot_json
        routes = {route['id']: route for route in snapshot.get('routes', [])}
        prompts = {prompt['id']: prompt for prompt in snapshot.get('prompts', [])}
        is_judge = snapshot.get('kind') == 'evaluation'
        failures = sum(item.status == 'failed' for item in items)
        processed = sum(item.status in {'completed', 'failed'} for item in items)
        for item in items:
            if item.status != 'queued' or (item_ids is not None and item.id not in item_ids):
                continue
            await self.db.refresh(run)
            if run.status in {'cancelled', 'cancelling'}:
                break
            started = perf_counter()
            route = snapshot['judge']['route'] if is_judge else routes.get(item.route_id)
            node_id = 'judge' if is_judge else 'generate'
            route_info = {'route_id': route['id'], 'provider': route['provider_name']} if route else {}
            previous = (await self.db.execute(select(EvaluationAttempt).where(EvaluationAttempt.run_item_id == item.id))).scalars().all()
            sequence = max((a.route_snapshot_json.get('sequence', 0) for a in previous), default=0) + 1
            route_info['sequence'] = sequence
            attempt_kind = 'retry' if previous else 'initial'
            output = None
            item.status = 'running'
            route_info.update(started_at=datetime.utcnow().isoformat() + 'Z', http_attempts=0)
            attempt_record = EvaluationAttempt(run_item_id=item.id, node_id=node_id, kind=attempt_kind, route_snapshot_json=dict(route_info))
            self.db.add(attempt_record)
            run.progress_json = {'completed': processed, 'total': len(items), 'failed': failures,
                                 'active_item_id': item.id, 'attempt': sequence, 'http_attempt': 0,
                                 'active_started_at': route_info['started_at'], 'timeout_seconds': (route or {}).get('timeout_seconds', 60)}
            await self.db.commit()

            async def report_http_attempt(number):
                await self.db.refresh(run)
                if number > 1 and run.status in {'cancelled', 'cancelling'}:
                    raise ProviderExecutionError('cancelled', 'Повторный HTTP-запрос не отправлен: запуск отменяется.')
                route_info['http_attempts'] = number
                attempt_record.route_snapshot_json = dict(route_info)
                run.progress_json = {**run.progress_json, 'http_attempt': number}
                await self.db.commit()

            try:
                if route is None:
                    raise ValueError('ModelRoute snapshot is unavailable')
                if is_judge:
                    source = snapshot['evaluation_inputs'][item.id]
                    criteria = snapshot['suite']['criteria']
                    text = judge_prompt(snapshot['judge']['prompt']['template'], source, criteria)
                else:
                    source = await self.db.get(EvaluationDatasetItem, item.dataset_item_id)
                    if source is None:
                        raise ValueError('Dataset item is unavailable')
                    prompt = prompts.get(item.prompt_version_id)
                    if prompt:
                        text = render_prompt(prompt['template'], source.input_json)
                    elif snapshot.get('kind') == 'generation':
                        raise ValueError('PromptVersion snapshot is unavailable')
                    else:
                        # Compatibility for already queued, pre-versioned snapshots.
                        text = source.input_json.get('text') or source.input_json.get('prompt') or str(source.input_json)
                if route['provider_name'].lower() == 'offline':
                    if is_judge:
                        output = {'text': json.dumps({'scores': {c['key']: c.get('max_score', 1.0) for c in criteria}, 'rationale': 'OFFLINE FIXTURE: not a quality assessment'})}
                    else:
                        output = {'text': f'[offline:{item.route_id[:8]}] {text}'}
                else:
                    output = await generate_external(route, NormalizedGenerationRequest(model=route['model_identifier'], prompt=text, max_output_tokens=snapshot.get('policy', {}).get('max_output_tokens', 1024)), on_attempt=report_http_attempt)
                if output.get('finish_reason') in {'MAX_TOKENS', 'length'}:
                    raise ProviderExecutionError('truncated_response', 'Ответ оборван по лимиту выходных токенов. Увеличьте лимит в настройках нового запуска.', retryable=False)
                if output.get('finish_reason') in {'SAFETY', 'RECITATION', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII', 'content_filter'}:
                    raise ProviderExecutionError('blocked_response', 'Провайдер заблокировал ответ; оценка не вычислена.', retryable=False)
                if not isinstance(output.get('text'), str) or not output['text'].strip():
                    raise ProviderExecutionError('empty_response', 'Провайдер вернул пустой текстовый ответ. Попробуйте повторить запись.', retryable=True)
                if is_judge:
                    value = parse_judgment(output.get('text', ''), criteria, snapshot['suite']['quality_threshold'], snapshot['suite'].get('scoring_mode', 'weighted'))
                    value['_attempt'] = sequence
                    self.db.add(EvaluationResult(run_item_id=item.id, evaluator_id='judge', status='completed', value_json=value, numeric_score=value['score']))
                item.output_json, item.status, item.error_json = output, 'completed', None
                attempt_record.output_json = output
            except Exception as exc:
                failures += 1
                if isinstance(exc, ProviderExecutionError):
                    error = {'code': exc.code, 'message': exc.message, 'retryable': exc.retryable}
                else:
                    error = {'code': 'execution_error', 'message': 'Execution failed: input or saved configuration is invalid', 'retryable': False}
                item.status, item.error_json, item.output_json = 'failed', error, None
                attempt_record.output_json, attempt_record.error_json = output, error
                if is_judge:
                    self.db.add(EvaluationResult(run_item_id=item.id, evaluator_id='judge', status='failed', value_json={'error': error, '_attempt': sequence}, numeric_score=None))
            attempt_record.latency_ms = max(1, round((perf_counter() - started) * 1000))
            attempt_record.route_snapshot_json = {**route_info, 'completed_at': datetime.utcnow().isoformat() + 'Z'}
            # Refresh only the Run to observe cancellation while a provider was pending.
            await self.db.refresh(run)
            processed += 1
            run.progress_json = {'completed': processed, 'total': len(items), 'failed': failures}
            await self.db.commit()
        await self.db.refresh(run)
        if run.status in {'cancelled', 'cancelling'}:
            for item in items:
                if item.status == 'queued':
                    item.status = 'cancelled'
            run.status, run.completed_at = 'cancelled', datetime.utcnow()
            await self.db.commit()
        else:
            run.status = 'completed_with_errors' if failures else 'completed'
            run.completed_at = datetime.utcnow()
            await self.db.commit()
