import asyncio
import os
import time
import unittest
from unittest.mock import patch
import httpx
from app.services.v1_providers import EnvironmentSecretResolver, GoogleGenerateContentAdapter, ImagePart, NormalizedGenerationRequest, OpenRouterChatAdapter, ProviderConfigurationError, ProviderExecutionError, generate_external, list_provider_models


class ProviderContractTests(unittest.TestCase):
    def setUp(self):
        self.request = NormalizedGenerationRequest(model="vision-model", prompt="Describe image", images=(ImagePart("image/png", "aGVsbG8="),))

    def test_google_payload_uses_inline_data_and_mime(self):
        url, headers, payload = GoogleGenerateContentAdapter.build_request(self.request, "secret-value")
        self.assertEqual(url, "https://generativelanguage.googleapis.com/v1beta/models/vision-model:generateContent")
        self.assertEqual(headers["x-goog-api-key"], "secret-value")
        self.assertEqual(payload["contents"][0]["parts"][1], {"inlineData": {"mimeType": "image/png", "data": "aGVsbG8="}})

    def test_openrouter_payload_uses_base64_data_url(self):
        url, headers, payload = OpenRouterChatAdapter.build_request(self.request, "secret-value")
        self.assertEqual(url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer secret-value")
        self.assertEqual(payload["messages"][0]["content"][1]["image_url"]["url"], "data:image/png;base64,aGVsbG8=")

    def test_external_route_without_credential_fails_without_network(self):
        with self.assertRaises(ProviderExecutionError) as caught:
            asyncio.run(generate_external({"provider_name": "google", "model_identifier": "gemini", "timeout_seconds": 1}, self.request))
        self.assertEqual(caught.exception.code, "credential_unavailable")

    def test_google_response_is_normalized_and_retries_temporary_error(self):
        os.environ["LLM_TEST_PROVIDER_KEY"] = "local-secret"
        calls = []
        async def handler(request):
            calls.append(request)
            if len(calls) == 1: return httpx.Response(429, json={"error": {"message": "busy"}})
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "normalized"}]}}], "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2, "totalTokenCount": 5}})
        result = asyncio.run(generate_external({"provider_name": "google", "model_identifier": "gemini-test", "credential_ref": "env:LLM_TEST_PROVIDER_KEY", "timeout_seconds": 1}, self.request, transport=httpx.MockTransport(handler)))
        self.assertEqual(len(calls), 2)
        self.assertEqual(result, {"text": "normalized", "finish_reason": None, "usage": {"prompt": 3, "completion": 2, "total": 5}})

    def test_google_parts_and_finish_reason(self):
        result = GoogleGenerateContentAdapter.parse_response({'candidates': [{'content': {'parts': [{'text': 'internal', 'thought': True}, {'text': 'final '}, {'inlineData': {}}, {'text': 'answer'}]}, 'finishReason': 'STOP'}]})
        self.assertEqual(result['text'], 'final answer')
        self.assertEqual(result['finish_reason'], 'STOP')
        self.assertEqual(GoogleGenerateContentAdapter.parse_response({'candidates': [{'content': {'parts': [{'text': 'internal', 'thought': True}]}, 'finishReason': 'MAX_TOKENS'}]})['text'], '')
        self.assertEqual(OpenRouterChatAdapter.parse_response({'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}]})['finish_reason'], 'length')

    def test_openrouter_response_is_normalized(self):
        os.environ["LLM_TEST_PROVIDER_KEY"] = "local-secret"
        async def handler(request):
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}, "cost": 0.01})
        result = asyncio.run(generate_external({"provider_name": "openrouter", "model_identifier": "model", "credential_ref": "env:LLM_TEST_PROVIDER_KEY", "timeout_seconds": 1}, self.request, transport=httpx.MockTransport(handler)))
        self.assertEqual(result["text"], "ok")
        self.assertEqual(result["usage"]["cost"], 0.01)

    def test_provider_model_catalogs_are_normalized_and_free_models_first(self):
        os.environ["LLM_TEST_PROVIDER_KEY"] = "local-secret"

        async def google_handler(request):
            return httpx.Response(200, json={"models": [
                {"name": "models/gemini-generate", "displayName": "Gemini Generate", "inputTokenLimit": 100, "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embedding", "supportedGenerationMethods": ["embedContent"]},
            ]})

        google = asyncio.run(list_provider_models("google", "env:LLM_TEST_PROVIDER_KEY", httpx.MockTransport(google_handler)))
        self.assertEqual([item["id"] for item in google], ["gemini-generate"])
        self.assertIsNone(google[0]["is_free"])

        async def openrouter_handler(request):
            return httpx.Response(200, json={"data": [
                {"id": "paid/model", "name": "Paid", "context_length": 10, "pricing": {"prompt": "0.1", "completion": "0.2"}},
                {"id": "openrouter/free", "name": "Free Models Router", "context_length": 20, "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]}, "pricing": {"prompt": "0", "completion": "0"}},
            ]})

        openrouter = asyncio.run(list_provider_models("openrouter", "env:LLM_TEST_PROVIDER_KEY", httpx.MockTransport(openrouter_handler)))
        self.assertEqual(openrouter[0]["id"], "openrouter/free")
        self.assertTrue(openrouter[0]["is_free"])
        self.assertFalse(openrouter[1]["is_free"])

    def test_route_timeout_is_total_budget_including_retry(self):
        os.environ["LLM_TEST_PROVIDER_KEY"] = "local-secret"
        calls = []

        async def handler(request):
            calls.append(request)
            await asyncio.sleep(0.07)
            return httpx.Response(429, json={"error": {"message": "busy"}})

        started = time.perf_counter()
        with self.assertRaises(ProviderExecutionError) as caught:
            asyncio.run(generate_external({"provider_name": "google", "model_identifier": "gemini-test", "credential_ref": "env:LLM_TEST_PROVIDER_KEY", "timeout_seconds": 0.1}, self.request, transport=httpx.MockTransport(handler)))
        elapsed = time.perf_counter() - started
        self.assertEqual(caught.exception.code, "timeout")
        self.assertEqual(len(calls), 1)
        self.assertLess(elapsed, 0.18)

    def test_environment_reference_is_resolved_without_storing_secret(self):
        os.environ["LLM_TEST_PROVIDER_KEY"] = "local-secret"
        self.assertEqual(EnvironmentSecretResolver().resolve("env:LLM_TEST_PROVIDER_KEY"), "local-secret")
        with self.assertRaises(ProviderConfigurationError): EnvironmentSecretResolver().resolve("local-secret")
        with self.assertRaises(ProviderConfigurationError): EnvironmentSecretResolver().resolve("env:missing-key")

    def test_environment_reference_falls_back_to_windows_user_scope(self):
        os.environ.pop("LLM_TEST_USER_SCOPE_KEY", None)
        with patch("app.services.v1_providers._read_windows_user_environment", return_value="user-secret"):
            resolver = EnvironmentSecretResolver()
            self.assertTrue(resolver.is_available("env:LLM_TEST_USER_SCOPE_KEY"))
            self.assertEqual(resolver.resolve("env:LLM_TEST_USER_SCOPE_KEY"), "user-secret")
        with patch("app.services.v1_providers._read_windows_user_environment", return_value=None):
            self.assertFalse(EnvironmentSecretResolver().is_available("env:LLM_TEST_USER_SCOPE_KEY"))


if __name__ == "__main__":
    unittest.main()
