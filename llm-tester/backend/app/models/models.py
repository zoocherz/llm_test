from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class ProviderType(str, enum.Enum):
    """Типы провайдеров"""
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    GIGACHAT = "gigachat"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    YANDEX = "yandex"
    MISTRAL = "mistral"
    GROQ = "groq"
    TOGETHER = "together"
    DEEPINFRA = "deepinfra"
    LEAPWORK = "leapwork"
    OTHER = "other"


class Provider(Base):
    """Модель провайдера LLM"""
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    provider_type = Column(SQLEnum(ProviderType), nullable=False)
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(500), nullable=True)  # Для кастомных URL
    priority = Column(Integer, default=10)  # Приоритет в пуле (меньше = выше приоритет)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    test_runs = relationship("TestRun", back_populates="provider")


class Task(Base):
    """Модель задачи (сценария тестирования)"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    judge_prompt = Column(Text, nullable=False)  # Промт для судьи
    output_schema = Column(JSON, nullable=True)  # Ожидаемая схема вывода (JSON Schema)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    test_cases = relationship("TestCase", back_populates="task", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="task", cascade="all, delete-orphan")


class TestCase(Base):
    """Модель тест-кейса"""
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    prompt = Column(Text, nullable=False)  # Промт для тестируемой модели
    input_text = Column(Text, nullable=True)  # Входной текст
    input_images = Column(JSON, nullable=True)  # Список изображений (base64 или URL)
    expected_output = Column(Text, nullable=True)  # Ожидаемый вывод (для справки)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    task = relationship("Task", back_populates="test_cases")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")


class TestRun(Base):
    """Модель запуска теста"""
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)  # NULL если использовался пул
    model_name = Column(String(200), nullable=False)  # Тестируемая модель
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_cost = Column(Float, default=0.0)
    total_time = Column(Float, default=0.0)
    average_judge_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    task = relationship("Task", back_populates="test_runs")
    provider = relationship("Provider", back_populates="test_runs")
    results = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")


class TestResult(Base):
    """Модель результата тест-кейса"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    provider_used = Column(String(100), nullable=False)  # Какой провайдер фактически использовался
    model_response = Column(Text, nullable=False)  # Ответ модели
    response_time = Column(Float, nullable=False)  # Время ответа в секундах
    cost = Column(Float, default=0.0)  # Стоимость запроса
    tokens_used = Column(JSON, nullable=True)  # {prompt: int, completion: int, total: int}
    error_message = Column(Text, nullable=True)  # Сообщение об ошибке если была
    fallback_count = Column(Integer, default=0)  # Сколько раз переключались между провайдерами
    
    # Оценка судьи
    judge_score = Column(Float, nullable=True)  # Оценка от 0 до 1
    judge_feedback = Column(Text, nullable=True)  # Комментарий судьи
    judge_raw_response = Column(Text, nullable=True)  # Сырой ответ судьи
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    test_run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCase", back_populates="results")
