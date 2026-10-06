import asyncio
import json
import os
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from app.models.evaluation_schemas import RouteCreateRequest
from app.services.additional_providers import PRESETS, OAUTH_URL, normalize_capabilities, parse_response
from app.services.v1_providers import generate_external, list_provider_models, NormalizedGenerationRequest, ProviderExecutionError, ImagePart


class AdditionalProvidersTests(unittest.TestCase):
    def caps(self, provider):
        return normalize_capabilities(provider, {'base_url': 'https://synthetic.test:9443/custom', 'folder_id': 'test-folder'})

    def route(self, provider):
        return {'provider_name': provider, 'capabilities_json': self.caps(provider), 'credential_ref': 'env:ADDITIONAL_TEST_KEY', 'timeout_seconds': 2}

    def response(self, provider, text='final', reason=None):
        if provider == 'anthropic':
            return {'content': [{'type': 'thinking', 'thinking': 'not final'}, {'type': 'text', 'text': text}], 'stop_reason': reason or 'end_turn', 'usage': {'input_tokens': 2, 'output_tokens': 3}}
        return {'choices': [{'message': {'content': text, 'reasoning_content': 'not final'}, 'finish_reason': reason or 'stop'}], 'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5}}

    def test_all_twelve_wire_contracts(self):
        self.assertEqual(len(PRESETS), 12)
        for provider, preset in PRESETS.items():
            with self.subTest(provider=provider), patch.dict(os.environ, {'ADDITIONAL_TEST_KEY': 'synthetic-key'}):
                calls, progress = [], []
                async def handler(request):
                    calls.append(request)
                    if str(request.url) == OAUTH_URL:
                        self.assertEqual(request.headers['authorization'], 'Basic synthetic-key')
                        self.assertIn(b'scope=GIGACHAT_API_PERS', request.content)
                        return httpx.Response(200, json={'access_token': 'synthetic-access-token', 'expires_at': 9999999999999})
                    self.assertEqual(str(request.url), 'https://synthetic.test:9443/custom/' + ('messages' if provider == 'anthropic' else 'chat/completions'))
                    body = json.loads(request.content)
                    self.assertEqual(body['messages'], [{'role': 'user', 'content': 'hello'}])
                    self.assertEqual(body[preset['token_field']], 555)
                    self.assertNotIn('temperature', body)
                    self.assertFalse(body['stream'])
                    if provider == 'anthropic':
                        self.assertEqual(request.headers['x-api-key'], 'synthetic-key')
                        self.assertEqual(request.headers['anthropic-version'], '2023-06-01')
                    elif provider == 'yandex':
                        self.assertEqual(request.headers['authorization'], 'Api-Key synthetic-key')
                        self.assertEqual(request.headers['openai-project'], 'test-folder')
                        self.assertEqual(body['model'], 'gpt://test-folder/test-model')
                    else:
                        self.assertEqual(request.headers['authorization'], 'Bearer ' + ('synthetic-access-token' if provider == 'gigachat' else 'synthetic-key'))
                    return httpx.Response(200, json=self.response(provider))
                async def report(number): progress.append(number)
                result = asyncio.run(generate_external(self.route(provider), NormalizedGenerationRequest(model='test-model', prompt='hello', max_output_tokens=555), transport=httpx.MockTransport(handler), on_attempt=report))
                self.assertEqual(result['text'], 'final')
                self.assertEqual(result['usage']['total'], 5)
                self.assertNotIn('synthetic-key', json.dumps(result))
                self.assertEqual(progress, [1])
                self.assertEqual(len(calls), 2 if provider == 'gigachat' else 1)

    def test_catalogs_and_claude_pagination(self):
        for provider, preset in PRESETS.items():
            with self.subTest(provider=provider), patch.dict(os.environ, {'ADDITIONAL_TEST_KEY': 'synthetic-key'}):
                pages = []
                async def handler(request):
                    if str(request.url) == OAUTH_URL:
                        return httpx.Response(200, json={'access_token': 'temporary'})
                    pages.append(request)
                    self.assertEqual(request.url.path, '/custom/models')
                    if provider == 'anthropic' and len(pages) == 1:
                        return httpx.Response(200, json={'data': [{'id': 'one', 'display_name': 'First'}], 'has_more': True, 'last_id': 'one'})
                    if provider == 'anthropic': self.assertEqual(request.url.params['after_id'], 'one')
                    return httpx.Response(200, json={'data': [{'id': 'two'}, {'id': 'disabled', 'active': False}], 'has_more': False})
                query = list_provider_models(provider, 'env:ADDITIONAL_TEST_KEY', httpx.MockTransport(handler), base_url='https://synthetic.test:9443/custom', folder_id='test-folder')
                if preset['catalog']:
                    rows = asyncio.run(query)
                    self.assertEqual({r['id'] for r in rows}, {'one', 'two'} if provider == 'anthropic' else {'two'})
                    self.assertTrue(all(r['is_free'] is None for r in rows))
                else:
                    with self.assertRaises(ProviderExecutionError) as caught: asyncio.run(query)
                    self.assertEqual(caught.exception.code, 'catalog_unavailable')
                    self.assertEqual(pages, [])

    def test_configuration_and_https(self):
        for provider in PRESETS:
            with self.subTest(provider=provider):
                route = RouteCreateRequest(provider_name=provider, model_identifier='test', credential_ref='env:ADDITIONAL_TEST_KEY', capabilities=self.caps(provider))
                self.assertEqual(route.capabilities['sampling_policy'], 'provider_default')
                with self.assertRaises(ValidationError): RouteCreateRequest(provider_name=provider, model_identifier='test', capabilities=self.caps(provider))
                for url in ['http://example.test/v1', 'https://user:secret@example.test/v1', 'https://example.test/v1?api_key=secret', 'https://{workspace}.test/v1']:
                    with self.assertRaises(ValueError): normalize_capabilities(provider, {'base_url': url})
        with self.assertRaises(ValueError): normalize_capabilities('yandex', {})
        with self.assertRaises(ValueError): normalize_capabilities('gigachat', {'scope': 'wrong'})
        with self.assertRaises(ValueError): normalize_capabilities('qwen', {})

    def test_error_and_retry_contracts(self):
        for provider in PRESETS:
            with self.subTest(provider=provider), patch.dict(os.environ, {'ADDITIONAL_TEST_KEY': 'synthetic-key'}):
                calls = []
                route = self.route(provider)
                route['capabilities_json']['auth_mode'] = 'access_token'
                async def handler(request):
                    calls.append(request)
                    return httpx.Response(429, json={'error': 'private server body'}) if len(calls) == 1 else httpx.Response(200, json=self.response(provider))
                result = asyncio.run(generate_external(route, NormalizedGenerationRequest(model='test', prompt='hello'), transport=httpx.MockTransport(handler)))
                self.assertEqual(result['text'], 'final')
                self.assertEqual(len(calls), 2)
        for reason, code in [('tool_use', 'unsupported_response'), ('pause_turn', 'unsupported_response')]:
            with self.assertRaises(ProviderExecutionError) as caught: parse_response('anthropic', self.response('anthropic', reason=reason))
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(parse_response('anthropic', self.response('anthropic', reason='max_tokens'))['finish_reason'], 'length')
        self.assertEqual(parse_response('anthropic', self.response('anthropic', reason='refusal'))['finish_reason'], 'content_filter')
        for bad in [{}, {'choices': []}, {'choices': [{'message': {'content': 42}}]}]:
            with self.assertRaises(ProviderExecutionError): parse_response('groq', bad)

    def test_oauth_failure_and_total_timeout_no_secret_leak(self):
        with patch.dict(os.environ, {'ADDITIONAL_TEST_KEY': 'synthetic-private-key'}):
            async def denied(request): return httpx.Response(401, json={'error': 'synthetic-private-key'})
            with self.assertRaises(ProviderExecutionError) as caught:
                asyncio.run(generate_external(self.route('gigachat'), NormalizedGenerationRequest(model='test', prompt='hello'), transport=httpx.MockTransport(denied)))
            self.assertEqual(caught.exception.code, 'http_401')
            self.assertNotIn('synthetic-private-key', caught.exception.message)
            calls = []
            async def slow(request):
                calls.append(request)
                await asyncio.sleep(0.2)
                return httpx.Response(200, json={'access_token': 'temporary'})
            route = self.route('gigachat'); route['timeout_seconds'] = 0.02
            with self.assertRaises(ProviderExecutionError) as caught:
                asyncio.run(generate_external(route, NormalizedGenerationRequest(model='test', prompt='hello'), transport=httpx.MockTransport(slow)))
            self.assertEqual(caught.exception.code, 'timeout')
            self.assertEqual(len(calls), 1)

    def test_provider_specific_stop_reasons(self):
        for provider, reason, expected in [('gigachat', 'blacklist', 'content_filter'), ('mistral', 'model_length', 'length')]:
            parsed = parse_response(provider, {'choices': [{'message': {'content': 'partial'}, 'finish_reason': reason}]})
            self.assertEqual(parsed['finish_reason'], expected)

    def test_images_rejected_before_network(self):
        with patch.dict(os.environ, {'ADDITIONAL_TEST_KEY': 'synthetic-key'}):
            for provider in PRESETS:
                with self.subTest(provider=provider), self.assertRaises(ProviderExecutionError) as caught:
                    asyncio.run(generate_external(self.route(provider), NormalizedGenerationRequest(model='test', prompt='hello', images=(ImagePart('image/png', 'AA=='),))))
                self.assertEqual(caught.exception.code, 'unsupported_modality')
