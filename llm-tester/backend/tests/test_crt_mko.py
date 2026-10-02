import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from app.models.evaluation_schemas import RouteCreateRequest
from app.services.v1_providers import CrtMkoAdapter, NormalizedGenerationRequest, ProviderExecutionError, generate_external, list_provider_models, crt_base_url
from app.services.crt_response import final_text


class CrtMkoTests(unittest.TestCase):
    def test_observed_response_contract(self):
        result = CrtMkoAdapter.parse_response({'done': True, 'done_reason': 'stop', 'message': {'content': 'OK\n'}, 'prompt_eval_count': 27, 'eval_count': 3})
        self.assertEqual(result, {'text': 'OK\n', 'finish_reason': 'stop', 'usage': {'prompt': 27, 'completion': 3, 'total': 30}})
        for bad in [{}, {'done': False, 'message': {'content': 'partial'}}, {'done': True, 'data': 'wrong shape'}]:
            with self.assertRaises(ProviderExecutionError):
                CrtMkoAdapter.parse_response(bad)

    def test_no_secret_sent_and_catalog(self):
        calls = []
        async def handler(request):
            calls.append(request)
            self.assertEqual(str(request.url), 'http://mko.test:8088/custom/api/' + ('models' if request.method == 'GET' else 'completions'))
            self.assertNotIn('authorization', request.headers)
            self.assertNotIn('x-api-key', request.headers)
            if request.method == 'GET':
                return httpx.Response(200, json={'error': False, 'data': [{'name': 'test-model', 'engine': 'stc_llama'}, {'name': 'other', 'engine': 'other'}]})
            payload = json.loads(request.content)
            self.assertEqual(payload['input_text'], 'synthetic')
            self.assertTrue(payload['exclude_from_history'])
            return httpx.Response(200, json={'done': True, 'done_reason': 'stop', 'message': {'content': 'OK'}})
        transport = httpx.MockTransport(handler)
        with patch('app.services.v1_providers.EnvironmentSecretResolver.resolve', side_effect=AssertionError('Must not resolve secrets')):
            catalog = asyncio.run(list_provider_models('crt_mko', 'env:UNUSED', transport, base_url='http://mko.test:8088/custom/api', allow_insecure_http=True))
            result = asyncio.run(generate_external({'provider_name': 'crt_mko', 'capabilities_json': {'allow_insecure_http': True, 'base_url': 'http://mko.test:8088/custom/api'}}, NormalizedGenerationRequest(model='test-model', prompt='synthetic'), transport=transport))
        self.assertEqual([row['id'] for row in catalog], ['test-model'])
        self.assertEqual(result['text'], 'OK')
        self.assertEqual(len(calls), 2)

    def test_http_consent_required(self):
        with self.assertRaises(ValidationError):
            RouteCreateRequest(provider_name='crt_mko', model_identifier='test')
        with self.assertRaises(ProviderExecutionError) as caught:
            asyncio.run(generate_external({'provider_name': 'crt_mko', 'capabilities_json': {'base_url': 'http://mko.test/api/v1'}}, NormalizedGenerationRequest(model='test', prompt='never sent')))
        self.assertEqual(caught.exception.code, 'insecure_transport')

    def test_https_and_invalid_endpoints(self):
        route = RouteCreateRequest(provider_name='crt_mko', model_identifier='test', capabilities={'base_url': 'https://mko.test:9443/custom/'})
        self.assertEqual(route.capabilities['base_url'], 'https://mko.test:9443/custom')
        for value in ['', 'ftp://mko.test', 'https://name:password@mko.test', 'https://mko.test?key=secret', 'https://mko.test#fragment', 'http://mko.test:bad', 'https://mko.test/white space']:
            with self.subTest(value=value), self.assertRaises(ProviderExecutionError):
                crt_base_url({'base_url': value, 'allow_insecure_http': True})

    def test_response_markup_preserves_original_and_literal_escapes(self):
        raw = "```xml\n<thought>internal</thought>\n```xml\n<thought>more</thought>\nFinal answer\nsecond line\n```"
        parsed = CrtMkoAdapter.parse_response({'done': True, 'message': {'content': raw}})
        self.assertEqual(parsed['text'], 'Final answer\nsecond line')
        self.assertEqual(parsed['raw_text'], raw)
        self.assertEqual(final_text('<thought>internal</thought>\n```json\n{"scores": {}}\n```'), '{"scores": {}}')
        self.assertEqual(final_text('<thought>internal</thought>\n```python\nprint(1)\n```'), '```python\nprint(1)\n```')
        self.assertEqual(final_text('<think>unfinished'), '')
        self.assertEqual(final_text('<analysis>only reasoning</analysis>'), '')
        self.assertEqual(final_text('```\nAnswer\n```'), 'Answer')
        for text in [r'literal \n and thought xml', '<invoice>keep</invoice>', '```python\nprint(1)\n```', 'A thought about xml']:
            self.assertEqual(final_text(text), text)

    def test_transport_diagnostics_and_http_attempts(self):
        route = {'provider_name': 'crt_mko', 'capabilities_json': {'base_url': 'https://mko.test/api/v1'}}
        request = NormalizedGenerationRequest(model='test', prompt='synthetic')
        for response, code in [(httpx.Response(200, text='<html>private body</html>'), 'invalid_json'), (httpx.Response(200, json=[]), 'invalid_response'), (httpx.Response(200, json={'error': 'private error'}), 'provider_error'), (httpx.Response(302, headers={'location': 'https://other.test'}), 'http_302')]:
            async def handler(req): return response
            with self.subTest(code=code), self.assertRaises(ProviderExecutionError) as caught:
                asyncio.run(generate_external(route, request, transport=httpx.MockTransport(handler)))
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('private', caught.exception.message)
        calls, progress = [], []
        async def retry_handler(req):
            calls.append(req)
            return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json={'done': True, 'message': {'content': 'OK'}})
        async def report(number): progress.append(number)
        result = asyncio.run(generate_external(route, request, transport=httpx.MockTransport(retry_handler), on_attempt=report))
        self.assertEqual(result['text'], 'OK')
        self.assertEqual(progress, [1, 2])
