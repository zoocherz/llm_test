from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Приложение
    APP_NAME: str = "LLM Tester"
    DEBUG: bool = True
    
    # База данных
    DATABASE_URL: str = "sqlite+aiosqlite:///./llm_tester.db"
    
    # Безопасность (на будущее)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Лимиты
    MAX_TEST_HISTORY: int = 100
    MAX_FALLBACK_ATTEMPTS: int = 5
    DEFAULT_TIMEOUT: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
