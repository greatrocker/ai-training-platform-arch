import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    model_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(20), default="detect")  # detect / segment
    display_order: Mapped[int] = mapped_column(Integer, nullable=True)
    base_weight_path: Mapped[str] = mapped_column(String(500), nullable=True)
    arch_config_path: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainingJob(Base):
    __tablename__ = "training_job"
    job_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, nullable=True)  # cross-service ref
    model_key: Mapped[str] = mapped_column(String(50), ForeignKey("model_registry.model_key"), nullable=True)
    params_json: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)  # queued/running/completed/failed
    output_model_path: Mapped[str] = mapped_column(String(500), nullable=True)
    metrics_json: Mapped[str] = mapped_column(String, nullable=True)
    training_mode: Mapped[str] = mapped_column(String(20), default="full")  # full / incremental
    parent_job_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, nullable=True)
    replay_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    freeze_backbone: Mapped[bool] = mapped_column(Boolean, nullable=True)
    progress_current_epoch: Mapped[int] = mapped_column(Integer, nullable=True)
    progress_total_epochs: Mapped[int] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=True)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)
