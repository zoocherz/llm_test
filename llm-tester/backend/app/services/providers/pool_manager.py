from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Provider, ProviderType
from app.services.providers.factory import ProviderFactory
from app.services.providers.base import BaseProvider, LLMResponse, LLMError


class PoolManager:
    """Менеджер пула провайдеров с fallback логикой"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._providers_cache: List[Provider] = []
        self._last_refresh = 0
    
    async def get_active_providers(self) -> List[Provider]:
        """Получение активных провайдеров отсортированных по приоритету"""
        result = await self.db.execute(
            select(Provider)
            .where(Provider.is_active == True)
            .order_by(Provider.priority.asc())
        )
        return list(result.scalars().all())
    
    async def generate_with_fallback(
        self,
        prompt: str,
        model: str,
        input_text: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_attempts: int = 5,
        **kwargs
    ) -> Tuple[LLMResponse, str, int]:
        """
        Генерация ответа с использованием пула провайдеров.
        
        Возвращает:
        - LLMResponse: ответ модели
        - str: название использованного провайдера
        - int: количество попыток (fallback'ов)
        """
        providers = await self.get_active_providers()
        
        if not providers:
            raise LLMError(
                message="No active providers available",
                provider="Pool",
                retryable=False
            )
        
        last_error = None
        attempts = 0
        
        for provider in providers[:max_attempts]:
            attempts += 1
            
            try:
                # Создаём экземпляр провайдера
                llm_provider = ProviderFactory.create(
                    provider_type=provider.provider_type,
                    api_key=provider.api_key,
                    base_url=provider.base_url
                )
                
                # Пробуем получить ответ
                response = await llm_provider.generate(
                    prompt=prompt,
                    model=model,
                    input_text=input_text,
                    input_images=input_images,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Успех! Проверяем что ответ валидный
                if not response.content or len(response.content.strip()) == 0:
                    raise LLMError(
                        message="Empty response from model",
                        provider=provider.name,
                        retryable=False
                    )
                
                return response, provider.name, attempts - 1
                
            except LLMError as e:
                last_error = e
                # Если ошибка не retryable, переходим к следующему
                if not e.retryable:
                    continue
                # Иначе пробуем следующего
                continue
                
            except Exception as e:
                last_error = LLMError(
                    message=str(e),
                    provider=provider.name,
                    retryable=True
                )
                continue
        
        # Все провайдеры исчерпаны
        provider_names = [p.name for p in providers]
        raise LLMError(
            message=f"All providers failed. Last error: {last_error.message if last_error else 'Unknown'}",
            provider=f"Pool ({', '.join(provider_names)})",
            retryable=False
        )
    
    async def validate_all_providers(self) -> List[Tuple[Provider, bool, Optional[str]]]:
        """Проверка всех активных провайдеров"""
        providers = await self.get_active_providers()
        results = []
        
        for provider in providers:
            try:
                llm_provider = ProviderFactory.create(
                    provider_type=provider.provider_type,
                    api_key=provider.api_key,
                    base_url=provider.base_url
                )
                
                is_valid, error = await llm_provider.validate_connection()
                results.append((provider, is_valid, error))
                
            except Exception as e:
                results.append((provider, False, str(e)))
        
        return results
