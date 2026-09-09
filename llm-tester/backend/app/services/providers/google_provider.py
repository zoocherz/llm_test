from typing import List, Dict, Any, Optional
import time
import httpx
from app.services.providers.base import BaseProvider, LLMResponse, LLMError


class GoogleProvider(BaseProvider):
    """Провайдер для Google AI Studio (Gemini)"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
    
    @property
    def provider_name(self) -> str:
        return "Google"
    
    def get_default_model(self) -> str:
        return "gemini-1.5-flash"
    
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
        
        full_text = prompt
        if input_text:
            full_text = f"{prompt}\n\n{input_text}"
        
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        # Добавляем изображения если есть
        if input_images:
            for img in input_images:
                # Поддержка base64 или URL
                if img.startswith("http"):
                    payload["contents"][0]["parts"].append({
                        "inline_data": {"mime_type": "image/jpeg", "data": img}
                    })
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            # Парсим ответ
            if "candidates" not in data or len(data["candidates"]) == 0:
                raise LLMError(
                    message="No candidates in response",
                    provider=self.provider_name,
                    retryable=False
                )
            
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Токены (если доступны)
            usage = data.get("usageMetadata", {})
            tokens_used = {
                "prompt": usage.get("promptTokenCount", 0),
                "completion": usage.get("candidatesTokenCount", 0),
                "total": usage.get("totalTokenCount", 0)
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
        # Цены для Gemini (примерные, нужно обновлять)
        # gemini-1.5-flash: $0.000075 / 1K input, $0.0003 / 1K output
        pricing = {
            "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
            "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
            "gemini-1.0-pro": {"input": 0.000125, "output": 0.000375},
        }
        
        rates = pricing.get(model, pricing["gemini-1.5-flash"])
        
        cost = (
            (prompt_tokens / 1000) * rates["input"] +
            (completion_tokens / 1000) * rates["output"]
        )
        
        return round(cost, 6)
