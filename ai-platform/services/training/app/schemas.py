import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelRegistryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_key: str
    task_type: str
    display_order: int | None
    is_active: bool


class TrainingJobIn(BaseModel):
    dataset_id: uuid.UUID
    model_key: str
    epochs: int = Field(default=100, ge=1, le=2000)
    batch_size: int = Field(default=16, ge=1, le=256)
    img_size: int = Field(default=640, ge=64, le=1920)
    learning_rate: float = Field(default=0.01, gt=0, le=1)
    optimizer: str = Field(default="SGD", pattern="^(SGD|Adam|AdamW)$")
    pretrained: bool = True
    device: str = "auto"
    # Early stopping: terminate if accuracy hasn't improved for this many
    # consecutive epochs. 0 disables early stopping (always run all epochs).
    patience: int = Field(default=30, ge=0, le=1000)
    training_mode: str = Field(default="full", pattern="^(full|incremental)$")
    base_job_id: uuid.UUID | None = None
    freeze_backbone: bool = False


class TrainingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    job_id: uuid.UUID
    dataset_id: uuid.UUID | None
    model_key: str | None
    params_json: str | None
    status: str | None
    output_model_path: str | None
    metrics_json: str | None
    training_mode: str
    parent_job_id: uuid.UUID | None
    freeze_backbone: bool | None
    progress_current_epoch: int | None
    progress_total_epochs: int | None
    started_at: datetime | None
    finished_at: datetime | None
