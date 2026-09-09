from typing import List, Dict, Any, Optional
import time
import httpx
from app.services.providers.base import BaseProvider, LLMResponse, LLMError


class OpenAIProvider(BaseProvider):
    """Провайдер для OpenAI"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or "https://api.openai.com/v1"
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    def get_default_model(self) -> str:
        return "gpt-3.5-turbo"
    
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
        
        url = f"{self.base_url}/chat/completions"
        
        # Подготовка сообщений
        messages = self._prepare_messages(prompt, input_text, input_images)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
        # OpenAI pricing
        pricing = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }
        
        rates = pricing.get(model, pricing["gpt-3.5-turbo"])
        
        cost = (
            (prompt_tokens / 1000) * rates["input"] +
            (completion_tokens / 1000) * rates["output"]
        )
        
        return round(cost, 6)
