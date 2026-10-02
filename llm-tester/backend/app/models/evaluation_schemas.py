from __future__ import annotations
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.services.prompt_rendering import validate_prompt
from app.services.v1_providers import crt_base_url, ProviderExecutionError
class DatasetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200); description: str | None = None; schema: dict[str, Any] = Field(default_factory=dict)
class DatasetVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_version_id: UUID | None = None
    schema: dict[str, Any] | None = None
class DatasetItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=200); input: dict[str, Any]
    reference: dict[str, Any] = Field(default_factory=dict); metadata: dict[str, Any] = Field(default_factory=dict); tags: list[str] = Field(default_factory=list)
class DatasetImportMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id_field: str = Field(min_length=1, max_length=200)
    input_text_field: str = Field(min_length=1, max_length=200)
    reference_field: str | None = Field(default=None, min_length=1, max_length=200)
    reference_format: Literal["json", "text"] = "json"
class PromptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200); template: str = Field(min_length=1)
    @model_validator(mode='after')
    def valid_template(self):
        validate_prompt(self.template)
        return self
class PipelineCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=200); definition: dict[str, Any] = Field(default_factory=lambda: {"nodes": [{"id": "generate", "kind": "generate"}], "edges": []})
    @model_validator(mode="after")
    def linear_pipeline(self):
        nodes = self.definition.get('nodes')
        if (not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict)
                or nodes[0].get('kind') != 'generate' or not isinstance(nodes[0].get('id'), str)
                or not nodes[0]['id'].strip() or self.definition.get('edges', []) != []
                or set(self.definition) - {'nodes', 'edges'} or set(nodes[0]) - {'id', 'kind'}):
            raise ValueError('Pipeline — порядок обработки, не схема ответа. Сейчас поддерживается один вызов модели: {"nodes":[{"id":"generate","kind":"generate"}],"edges":[]}. Формат ответа опишите в промпте.')
        return self
class RouteCreateRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=100); model_identifier: str = Field(min_length=1, max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=lambda: {"modalities": ["text"]}); credential_ref: str | None = Field(default=None, pattern=r"^env:[A-Z][A-Z0-9_]*$"); timeout_seconds: int = Field(default=60, ge=1, le=600)
    @model_validator(mode="after")
    def validate_transport(self):
        if self.provider_name.lower() == "crt_mko":
            try:
                self.capabilities["base_url"] = crt_base_url(self.capabilities)
            except ProviderExecutionError as exc:
                raise ValueError(exc.message) from None
            if self.credential_ref is not None:
                raise ValueError("ЦРТ МКО не использует ключ. Уберите ссылку на секрет.")
        return self
class PromptPreviewRequest(BaseModel):
    template: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)
class JudgeCriterion(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$"); weight: float = Field(default=1, gt=0, le=1)
    description: str = Field(default='', max_length=2000)
    min_score: float = Field(default=0, allow_inf_nan=False)
    max_score: float = Field(default=1, allow_inf_nan=False)
    @model_validator(mode="after")
    def valid_range(self):
        if self.min_score >= self.max_score: raise ValueError('Максимум шкалы должен быть больше минимума.')
        return self
class SuiteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200); criteria: list[JudgeCriterion] = Field(min_length=1); quality_threshold: float = Field(default=0.7, ge=0, le=1)
    scoring_mode: Literal["weighted", "independent"] = "weighted"
    @model_validator(mode="after")
    def validate_weights(self):
        if len({item.key for item in self.criteria}) != len(self.criteria): raise ValueError('Коды критериев должны быть уникальны.')
        if self.scoring_mode == 'weighted':
            if any(c.min_score != 0 or c.max_score != 1 for c in self.criteria): raise ValueError('Взвешенный режим использует шкалу 0..1. Для собственных шкал выберите независимые оценки.')
            if abs(sum(item.weight for item in self.criteria) - 1) > 0.000001: raise ValueError('Сумма весов критериев должна равняться 1 (например, 0.5 + 0.5).')
        return self
class RunRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_ids: list[UUID] = Field(min_length=1)
class ExecutionPolicy(BaseModel):
    max_output_tokens: int = Field(default=4096, ge=128, le=65536)
    mode: Literal["benchmark", "availability"] = "benchmark"; concurrency: int = Field(default=3, ge=1, le=20)
    request_timeout_seconds: int = Field(default=60, ge=1, le=600); budget_limit: float | None = Field(default=None, ge=0); fallback_enabled: bool = False
    @model_validator(mode="after")
    def forbid_benchmark_fallback(self):
        if self.mode == "benchmark" and self.fallback_enabled: raise ValueError("fallback is not allowed in benchmark mode")
        return self
class RunEstimateRequest(BaseModel):
    dataset_version_id: UUID; prompt_version_ids: list[UUID] = Field(min_length=1, max_length=3); candidate_route_ids: list[UUID] = Field(min_length=1, max_length=5)
    policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy); judge_enabled: Literal[False] = False
class RunCreateRequest(RunEstimateRequest):
    pipeline_version_id: UUID; suite_version_id: UUID | None = None
class RunEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_output_tokens: int = Field(default=4096, ge=128, le=65536)
    judge_route_id: UUID
    judge_prompt_id: UUID
    suite_version_id: UUID
class RunEstimateResponse(BaseModel):
    dataset_item_count: int; candidate_calls: int; judge_calls: int; total_calls: int; policy: ExecutionPolicy
