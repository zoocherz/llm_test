from typing import List, Dict, Any, Optional
from app.services.providers.base import BaseProvider, LLMResponse, LLMError
from app.models.models import ProviderType
from app.services.providers.google_provider import GoogleProvider
from app.services.providers.openrouter_provider import OpenRouterProvider
from app.services.providers.gigachat_provider import GigaChatProvider
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.openai_provider import OpenAIProvider


class ProviderFactory:
    """Фабрика для создания провайдеров"""
    
    _providers = {
        ProviderType.GOOGLE: GoogleProvider,
        ProviderType.OPENROUTER: OpenRouterProvider,
        ProviderType.GIGACHAT: GigaChatProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.OPENAI: OpenAIProvider,
    }
    
    @classmethod
    def create(cls, provider_type: ProviderType, api_key: str, base_url: Optional[str] = None) -> BaseProvider:
        """Создание экземпляра провайдера"""
        provider_class = cls._providers.get(provider_type)
        
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        return provider_class(api_key=api_key, base_url=base_url)
    
    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_class: type):
        """Регистрация нового провайдера"""
        cls._providers[provider_type] = provider_class
