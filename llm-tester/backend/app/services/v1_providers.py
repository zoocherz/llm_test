from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Literal
import httpx


class ProviderConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderExecutionError(Exception):
    code: str
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class ImagePart:
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
    base64_data: str


@dataclass(frozen=True)
class NormalizedGenerationRequest:
    model: str
    prompt: str
    images: tuple[ImagePart, ...] = field(default_factory=tuple)
    temperature: float = 0.0
    max_output_tokens: int = 1024


def _read_windows_user_environment(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
    except (FileNotFoundError, OSError):
        return None
    return value if isinstance(value, str) and value.strip() else None


class EnvironmentSecretResolver:
    def resolve(self, credential_ref: str) -> str:
        if not credential_ref.startswith("env:"):
            raise ProviderConfigurationError("credential_ref must use env:VARIABLE_NAME")
        name = credential_ref[4:]
        if not name or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for char in name):
            raise ProviderConfigurationError("credential_ref contains an invalid environment variable name")
        value = os.getenv(name) or _read_windows_user_environment(name)
        if not value:
            raise ProviderConfigurationError(f"credential reference {credential_ref} is unavailable")
        return value

    def is_available(self, credential_ref: str | None) -> bool:
        if not credential_ref:
            return False
        try:
            self.resolve(credential_ref)
            return True
        except ProviderConfigurationError:
            return False


class GoogleGenerateContentAdapter:
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    @staticmethod
    def build_request(request: NormalizedGenerationRequest, api_key: str):
        parts = [{"text": request.prompt}]
        parts.extend({"inlineData": {"mimeType": image.mime_type, "data": image.base64_data}} for image in request.images)
        return f"{GoogleGenerateContentAdapter.base_url}/models/{request.model}:generateContent", {"x-goog-api-key": api_key, "content-type": "application/json"}, {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_output_tokens}}
    @staticmethod
    def parse_response(data: dict) -> dict:
        try:
            candidate = data["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
            text = ''.join(part['text'] for part in parts if isinstance(part, dict) and not part.get('thought') and isinstance(part.get('text'), str))
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderExecutionError("invalid_response", "Google response has no text candidate") from exc
        usage = data.get("usageMetadata", {})
        return {"text": text, "finish_reason": candidate.get("finishReason"), "usage": {"prompt": usage.get("promptTokenCount", 0), "completion": usage.get("candidatesTokenCount", 0), "total": usage.get("totalTokenCount", 0)}}


class OpenRouterChatAdapter:
    base_url = "https://openrouter.ai/api/v1"
    @staticmethod
    def build_request(request: NormalizedGenerationRequest, api_key: str):
        content = [{"type": "text", "text": request.prompt}]
        content.extend({"type": "image_url", "image_url": {"url": f"data:{image.mime_type};base64,{image.base64_data}"}} for image in request.images)
        return f"{OpenRouterChatAdapter.base_url}/chat/completions", {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-Title": "LLM Evaluation Workbench"}, {"model": request.model, "messages": [{"role": "user", "content": content}], "temperature": request.temperature, "max_tokens": request.max_output_tokens}
    @staticmethod
    def parse_response(data: dict) -> dict:
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderExecutionError("invalid_response", "OpenRouter response has no text choice") from exc
        usage = data.get("usage", {})
        return {"text": text, "finish_reason": data["choices"][0].get("finish_reason"), "usage": {"prompt": usage.get("prompt_tokens", 0), "completion": usage.get("completion_tokens", 0), "total": usage.get("total_tokens", 0), "cost": data.get("cost")}}


class CrtMkoAdapter:
    base_url = "http://super-project-work.ru:8001/api/v1"

    @staticmethod
    def build_request(request: NormalizedGenerationRequest, api_key: str = ""):
        if request.images:
            raise ProviderExecutionError("unsupported_modality", "ЦРТ МКО: поддержан только текст.")
        return CrtMkoAdapter.base_url + "/completions", {"Content-Type": "application/json"}, {
            "model": request.model, "engine": "stc_llama", "input_text": request.prompt,
            "temperature": request.temperature, "stream": False,
            "exclude_from_history": True, "exclude_context": True,
        }

    @staticmethod
    def parse_response(data: dict) -> dict:
        if not isinstance(data, dict) or data.get("done") is not True:
            raise ProviderExecutionError("invalid_response", "ЦРТ МКО не вернул завершённый ответ.")
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderExecutionError("invalid_response", "ЦРТ МКО: отсутствует message.content.")
        prompt, completion = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
        prompt = prompt if type(prompt) is int and prompt >= 0 else 0
        completion = completion if type(completion) is int and completion >= 0 else 0
        return {"text": message["content"], "finish_reason": data.get("done_reason"),
                "usage": {"prompt": prompt, "completion": completion, "total": prompt + completion}}


async def list_provider_models(provider_name: str, credential_ref: str | None, transport: httpx.AsyncBaseTransport | None = None) -> list[dict]:
    provider = provider_name.lower()
    if provider not in {"google", "openrouter", "crt_mko"}:
        raise ProviderExecutionError("unsupported_provider", "Provider model catalog is not supported")
    api_key = None
    if credential_ref and provider != "crt_mko":
        try:
            api_key = EnvironmentSecretResolver().resolve(credential_ref)
        except ProviderConfigurationError as exc:
            raise ProviderExecutionError("credential_unavailable", "Model catalog credential is unavailable") from exc
    if provider == "google" and not api_key:
        raise ProviderExecutionError("credential_unavailable", "Google model catalog requires a credential reference")
    if provider == "google":
        url = f"{GoogleGenerateContentAdapter.base_url}/models?pageSize=1000"
        headers = {"x-goog-api-key": api_key}
    elif provider == "crt_mko":
        url, headers = CrtMkoAdapter.base_url + "/models", {}
    else:
        url = f"{OpenRouterChatAdapter.base_url}/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=20, transport=transport) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise ProviderExecutionError("timeout", "Provider model catalog timed out", True) from exc
    except httpx.TransportError as exc:
        raise ProviderExecutionError("network_error", "Provider model catalog request failed", True) from exc
    if response.status_code >= 400:
        raise ProviderExecutionError(f"http_{response.status_code}", "Provider model catalog returned an HTTP error", response.status_code in {408, 429} or response.status_code >= 500)
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderExecutionError("invalid_response", "Provider model catalog returned invalid JSON") from exc
    if provider == "crt_mko":
        if not isinstance(payload, dict) or payload.get("error") or not isinstance(payload.get("data"), list):
            raise ProviderExecutionError("invalid_response", "ЦРТ МКО: неверный формат каталога.")
        return [{"id": raw["name"], "display_name": raw["name"], "provider_name": provider,
                 "is_free": None, "input_modalities": ["text"], "output_modalities": ["text"]}
                for raw in payload["data"] if isinstance(raw, dict) and isinstance(raw.get("name"), str) and raw.get("engine") == "stc_llama"]
    if provider == "google":
        models = []
        for raw in payload.get("models", []):
            if "generateContent" not in raw.get("supportedGenerationMethods", []):
                continue
            model_id = str(raw.get("name", "")).removeprefix("models/")
            if not model_id:
                continue
            models.append({"id": model_id, "display_name": raw.get("displayName") or model_id, "provider_name": provider, "is_free": None, "context_window": raw.get("inputTokenLimit"), "input_modalities": ["text"], "output_modalities": ["text"]})
    else:
        models = []
        for raw in payload.get("data", []):
            model_id = raw.get("id")
            if not model_id:
                continue
            pricing = raw.get("pricing") or {}
            try:
                is_free = float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0
            except (TypeError, ValueError):
                is_free = False
            architecture = raw.get("architecture") or {}
            models.append({"id": model_id, "display_name": raw.get("name") or model_id, "provider_name": provider, "is_free": is_free, "context_window": raw.get("context_length"), "input_modalities": architecture.get("input_modalities") or ["text"], "output_modalities": architecture.get("output_modalities") or ["text"]})
    return sorted(models, key=lambda item: (item["is_free"] is not True, item["id"] != "openrouter/free", item["display_name"].lower()))

async def generate_external(route: dict, request: NormalizedGenerationRequest, attempts: int = 2, transport: httpx.AsyncBaseTransport | None = None) -> dict:
    provider = route["provider_name"].lower()
    adapter = {"google": GoogleGenerateContentAdapter, "openrouter": OpenRouterChatAdapter, "crt_mko": CrtMkoAdapter}.get(provider)
    if adapter is None:
        raise ProviderExecutionError("unsupported_provider", "ModelRoute provider is not supported by v1 executor")
    ref = route.get("credential_ref")
    if provider == "crt_mko" and route.get("capabilities_json", {}).get("allow_insecure_http") is not True:
        raise ProviderExecutionError("insecure_transport", "Подтвердите передачу текстов по HTTP в настройке ЦРТ МКО.")
    if not ref and provider != "crt_mko":
        raise ProviderExecutionError("credential_unavailable", "ModelRoute has no credential reference")
    try:
        api_key = "" if provider == "crt_mko" else EnvironmentSecretResolver().resolve(ref)
    except ProviderConfigurationError as exc:
        raise ProviderExecutionError("credential_unavailable", "ModelRoute credential is unavailable") from exc
    url, headers, payload = adapter.build_request(request, api_key)
    timeout = route.get("timeout_seconds", 60)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    error = ProviderExecutionError("timeout", "Provider request timed out", True)
    for attempt in range(attempts):
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise ProviderExecutionError("timeout", "Provider request timed out", True)
        try:
            async with asyncio.timeout(remaining):
                async with httpx.AsyncClient(timeout=remaining, transport=transport) as client:
                    response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                retryable = response.status_code in {408, 429} or response.status_code >= 500
                raise ProviderExecutionError(f"http_{response.status_code}", "Provider returned an HTTP error", retryable)
            return adapter.parse_response(response.json())
        except (httpx.TimeoutException, TimeoutError):
            error = ProviderExecutionError("timeout", "Provider request timed out", True)
        except httpx.TransportError:
            error = ProviderExecutionError("network_error", "Provider request failed", True)
        except ProviderExecutionError as exc:
            error = exc
        if not error.retryable or attempt + 1 == attempts:
            raise error
        delay = 0.2 * (attempt + 1)
        if deadline - loop.time() <= delay:
            raise ProviderExecutionError("timeout", "Provider request timed out", True)
        await asyncio.sleep(delay)
    raise error
