from typing import List, Dict, Any, Optional
import time
import httpx
import json
from app.services.providers.base import BaseProvider, LLMResponse, LLMError


class GigaChatProvider(BaseProvider):
    """Провайдер для GigaChat (Sber)"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        # Для GigaChat может потребоваться дополнительная аутентификация
        self.base_url = base_url or "https://gigachat.devices.sberbank.ru/api/v2"
        self.auth_token = None
    
    @property
    def provider_name(self) -> str:
        return "GigaChat"
    
    def get_default_model(self) -> str:
        return "GigaChat"
    
    async def _get_auth_token(self) -> str:
        """Получение токена аутентификации"""
        # API ключ может быть в формате client_id:client_secret или просто токен
        if ":" in self.api_key:
            client_id, client_secret = self.api_key.split(":", 1)
            
            url = "https://ngw-api.sberbank.ru/api/v2/oauth"
            payload = {
                "scope": "GIGACHAT_API_PERS",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=payload,
                    headers={
                        "Authorization": f"Basic {self.api_key}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                response.raise_for_status()
                data = response.json()
                self.auth_token = data.get("access_token")
        else:
            self.auth_token = self.api_key
        
        return self.auth_token
    
    async def generate(
        self,
        prompt: str,
        model: str,
        input_text: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> LLMResponse:
        start_time = time.time()
        
        # Получаем токен если нет
        if not self.auth_token:
            await self._get_auth_token()
        
        full_text = prompt
        if input_text:
            full_text = f"{prompt}\n\n{input_text}"
        
        url = f"{self.base_url}/chat/completions"
        
        messages = [{"role": "user", "content": full_text}]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            # Парсим ответ
            if "choices" not in data or len(data["choices"]) == 0:
                raise LLMError(
                    message="No choices in response",
                    provider=self.provider_name,
                    retryable=False
                )
            
            content = data["choices"][0]["message"]["content"]
            
            # Токены
            usage = data.get("usage", {})
            tokens_used = {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0)
            }
            
            response_time = time.time() - start_time
            
            # Оценка стоимости
            cost = await self.estimate_cost(
                model,
                tokens_used["prompt"],
                tokens_used["completion"]
            )
            
            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                response_time=response_time,
                cost=cost,
                model_name=model,
                raw_response=data
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Токен истёк, пробуем получить новый
                self.auth_token = None
                await self._get_auth_token()
                # Можно повторить запрос, но для простоты возвращаем ошибку
                raise LLMError(
                    message="Authentication failed, token refreshed",
                    provider=self.provider_name,
                    retryable=True
                )
            raise LLMError(
                message=f"HTTP Error: {e.response.status_code}",
                provider=self.provider_name,
                retryable=e.response.status_code >= 500
            )
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider=self.provider_name,
                retryable=True
            )
    
    async def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        # GigaChat pricing (примерные цены)
        pricing = {
            "GigaChat": {"input": 0.0, "output": 0.0},  # Часто бесплатно для тестов
            "GigaChat Pro": {"input": 0.001, "output": 0.002},
        }
        
        rates = pricing.get(model, pricing["GigaChat"])
        
        cost = (
            (prompt_tokens / 1000) * rates["input"] +
            (completion_tokens / 1000) * rates["output"]
        )
        
        return round(cost, 6)
