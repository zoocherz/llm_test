import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from app.models.evaluation_schemas import RouteCreateRequest
from app.services.v1_providers import CrtMkoAdapter, NormalizedGenerationRequest, ProviderExecutionError, generate_external, list_provider_models


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
            catalog = asyncio.run(list_provider_models('crt_mko', 'env:UNUSED', transport))
            result = asyncio.run(generate_external({'provider_name': 'crt_mko', 'capabilities_json': {'allow_insecure_http': True}}, NormalizedGenerationRequest(model='test-model', prompt='synthetic'), transport=transport))
        self.assertEqual([row['id'] for row in catalog], ['test-model'])
        self.assertEqual(result['text'], 'OK')
        self.assertEqual(len(calls), 2)

    def test_http_consent_required(self):
        with self.assertRaises(ValidationError):
            RouteCreateRequest(provider_name='crt_mko', model_identifier='test')
        with self.assertRaises(ProviderExecutionError) as caught:
            asyncio.run(generate_external({'provider_name': 'crt_mko'}, NormalizedGenerationRequest(model='test', prompt='never sent')))
        self.assertEqual(caught.exception.code, 'insecure_transport')
