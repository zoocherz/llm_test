from typing import List, Dict, Any, Optional
import time
import httpx
from app.services.providers.base import BaseProvider, LLMResponse, LLMError


class AnthropicProvider(BaseProvider):
    """Провайдер для Anthropic (Claude)"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self.base_url = base_url or "https://api.anthropic.com/v1"
    
    @property
    def provider_name(self) -> str:
        return "Anthropic"
    
    def get_default_model(self) -> str:
        return "claude-3-haiku-20240307"
    
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
        
        url = f"{self.base_url}/messages"
        
        # Подготовка контента
        messages_content = []
        if input_images:
            for img in input_images:
                if img.startswith("http"):
                    # URL изображения - нужно скачать и конвертировать в base64
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(img)
                        img_data = img_response.content
                        messages_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_data.decode('latin-1')
                            }
                        })
                else:
                    # Предполагаем что это base64
                    messages_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img
                        }
                    })
            
            messages_content.append({"type": "text", "text": full_text})
        else:
            messages_content = [{"type": "text", "text": full_text}]
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": messages_content}
            ],
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            # Парсим ответ
            content = ""
            if "content" in data and len(data["content"]) > 0:
                content = data["content"][0]["text"]
            
            # Токены
            usage = data.get("usage", {})
            tokens_used = {
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
                "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
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
        # Anthropic pricing
        pricing = {
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
        }
        
        rates = pricing.get(model, pricing["claude-3-haiku-20240307"])
        
        cost = (
            (prompt_tokens / 1000) * rates["input"] +
            (completion_tokens / 1000) * rates["output"]
        )
        
        return round(cost, 6)
