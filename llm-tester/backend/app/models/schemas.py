from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
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


# === Provider Schemas ===

class ProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: ProviderType
    api_key: str
    base_url: Optional[str] = None
    priority: int = Field(default=10, ge=1, le=100)
    is_active: bool = True


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ProviderResponse(ProviderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# === Task Schemas ===

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    judge_prompt: str
    output_schema: Optional[Dict[str, Any]] = None
    is_active: bool = True


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    judge_prompt: Optional[str] = None
    output_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# === TestCase Schemas ===

class TestCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    prompt: str
    input_text: Optional[str] = None
    input_images: Optional[List[str]] = None
    expected_output: Optional[str] = None


class TestCaseCreate(TestCaseBase):
    task_id: int


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    input_text: Optional[str] = None
    input_images: Optional[List[str]] = None
    expected_output: Optional[str] = None


class TestCaseResponse(TestCaseBase):
    id: int
    task_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# === TestRun Schemas ===

class TestRunCreate(BaseModel):
    task_id: int
    model_name: str
    provider_id: Optional[int] = None  # None = использовать пул


class TestRunResponse(BaseModel):
    id: int
    task_id: int
    provider_id: Optional[int]
    model_name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_cost: float
    total_time: float
    average_judge_score: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


# === TestResult Schemas ===

class TestResultResponse(BaseModel):
    id: int
    test_run_id: int
    test_case_id: int
    provider_used: str
    model_response: str
    response_time: float
    cost: float
    tokens_used: Optional[Dict[str, Any]]
    error_message: Optional[str]
    fallback_count: int
    judge_score: Optional[float]
    judge_feedback: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# === Statistics Schemas ===

class TestStatistics(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    average_response_time: float
    average_cost: float
    average_judge_score: Optional[float]
    models_tested: List[str]


# === Export Schemas ===

class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "xlsx"
