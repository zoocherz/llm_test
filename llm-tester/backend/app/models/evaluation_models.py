from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
def new_id() -> str: return str(uuid4())
class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationDatasetVersion(Base):
    __tablename__ = "evaluation_dataset_versions"; __table_args__ = (UniqueConstraint("dataset_id", "version_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("evaluation_datasets.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False); schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft"); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationDatasetItem(Base):
    __tablename__ = "evaluation_dataset_items"; __table_args__ = (UniqueConstraint("dataset_version_id", "external_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("evaluation_dataset_versions.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False); input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reference_json: Mapped[dict] = mapped_column(JSON, default=dict); metadata_json: Mapped[dict] = mapped_column(JSON, default=dict); tags_json: Mapped[list] = mapped_column(JSON, default=list)
class EvaluationAsset(Base):
    __tablename__ = "evaluation_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("evaluation_dataset_versions.id"), nullable=False)
    dataset_item_id: Mapped[str | None] = mapped_column(ForeignKey("evaluation_dataset_items.id")); role: Mapped[str] = mapped_column(String(40), default="input")
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False); original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False); byte_size: Mapped[int] = mapped_column(nullable=False); sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationPromptVersion(Base):
    __tablename__ = "evaluation_prompt_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); name: Mapped[str] = mapped_column(String(200), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False); version_number: Mapped[int] = mapped_column(default=1); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationPipelineVersion(Base):
    __tablename__ = "evaluation_pipeline_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); name: Mapped[str] = mapped_column(String(200), nullable=False)
    definition_json: Mapped[dict] = mapped_column(JSON, default=dict); status: Mapped[str] = mapped_column(String(20), default="published"); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationModelRoute(Base):
    __tablename__ = "evaluation_model_routes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(200), nullable=False); capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict); credential_ref: Mapped[str | None] = mapped_column(String(200))
    timeout_seconds: Mapped[int] = mapped_column(default=60); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationSuiteVersion(Base):
    __tablename__ = "evaluation_suite_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); name: Mapped[str] = mapped_column(String(200), nullable=False)
    evaluators_json: Mapped[list] = mapped_column(JSON, default=list); decision_rule_json: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); status: Mapped[str] = mapped_column(String(30), default="queued")
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False); progress_json: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime); completed_at: Mapped[datetime | None] = mapped_column(DateTime)
class EvaluationRunItem(Base):
    __tablename__ = "evaluation_run_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    dataset_item_id: Mapped[str] = mapped_column(ForeignKey("evaluation_dataset_items.id"), nullable=False); prompt_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    route_id: Mapped[str] = mapped_column(String(36), nullable=False); status: Mapped[str] = mapped_column(String(30), default="queued")
    output_json: Mapped[dict | None] = mapped_column(JSON); error_json: Mapped[dict | None] = mapped_column(JSON)
class EvaluationAttempt(Base):
    __tablename__ = "evaluation_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); run_item_id: Mapped[str] = mapped_column(ForeignKey("evaluation_run_items.id"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(100), nullable=False); route_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict); kind: Mapped[str] = mapped_column(String(20), default="initial")
    latency_ms: Mapped[int | None] = mapped_column(); output_json: Mapped[dict | None] = mapped_column(JSON); error_json: Mapped[dict | None] = mapped_column(JSON)
class EvaluationResult(Base):
    __tablename__ = "evaluation_results_v1"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id); run_item_id: Mapped[str] = mapped_column(ForeignKey("evaluation_run_items.id"), nullable=False)
    evaluator_id: Mapped[str] = mapped_column(String(100), nullable=False); status: Mapped[str] = mapped_column(String(30), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSON); numeric_score: Mapped[float | None] = mapped_column()
