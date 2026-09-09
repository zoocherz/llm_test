from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import time
import json
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Стандартный ответ от LLM"""
    content: str
    tokens_used: Dict[str, int]  # {prompt: int, completion: int, total: int}
    response_time: float
    cost: float
    model_name: str
    raw_response: Any  # Сырой ответ от API


@dataclass
class LLMError(Exception):
    """Ошибка при вызове LLM"""
    message: str
    provider: str
    retryable: bool = True


class BaseProvider(ABC):
    """Базовый класс для всех провайдеров"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
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
        """Генерация ответа от модели"""
        pass
    
    @abstractmethod
    async def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Оценка стоимости запроса"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Название провайдера"""
        pass
    
    async def validate_connection(self) -> Tuple[bool, Optional[str]]:
        """Проверка подключения и API ключа"""
        try:
            await self.generate(
                prompt="Say 'OK' if you can read this.",
                model=self.get_default_model(),
                max_tokens=10
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_default_model(self) -> str:
        """Модель по умолчанию для провайдера"""
        return "default"
    
    def _prepare_messages(
        self,
        prompt: str,
        input_text: Optional[str] = None,
        input_images: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Подготовка сообщений для API"""
        content = []
        
        # Добавляем текст
        full_text = prompt
        if input_text:
            full_text = f"{prompt}\n\n{input_text}"
        
        # Если есть изображения, используем мультимодальный формат
        if input_images:
            for img in input_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img}
                })
            
            content.append({
                "type": "text",
                "text": full_text
            })
            
            return [{"role": "user", "content": content}]
        else:
            return [{"role": "user", "content": full_text}]
