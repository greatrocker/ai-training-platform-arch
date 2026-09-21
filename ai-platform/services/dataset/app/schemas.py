import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetIn(BaseModel):
    name: str
    source_path: str = Field(description="Absolute Windows path, e.g. D:\\Videos\\lineA (drive must be mounted, see WINDOWS_DRIVE_MOUNTS)")
    source_type: str = Field(pattern="^(video|image_folder)$")
    frame_interval_sec: int | None = Field(default=None, ge=1, description="Video only, overrides default")
    filename_pattern: str | None = Field(
        default=None,
        description="image_folder only: fnmatch glob against filename, e.g. *Stitch_Img*. Folder is scanned recursively either way.",
    )


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dataset_id: uuid.UUID
    name: str | None
    source_path: str | None
    source_type: str | None
    filename_pattern: str | None
    status: str | None
    created_by: str | None
    created_at: datetime | None
    asset_count: int = 0


class DatasetAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: uuid.UUID
    dataset_id: uuid.UUID
    minio_path: str | None
    width: int | None
    height: int | None
    frame_index: int | None
    thumb_url: str | None = None
    raw_url: str | None = None
