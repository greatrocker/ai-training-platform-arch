import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Dataset(Base):
    __tablename__ = "dataset"
    dataset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    source_path: Mapped[str] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=True)  # video / image_folder
    filename_pattern: Mapped[str] = mapped_column(String(200), nullable=True)  # image_folder only, fnmatch glob
    status: Mapped[str] = mapped_column(String(20), nullable=True)      # pending/processing/ready/failed
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=True)


class DatasetAsset(Base):
    __tablename__ = "dataset_asset"
    asset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("dataset.dataset_id"))
    minio_path: Mapped[str] = mapped_column(String(500), nullable=True)
    width: Mapped[int] = mapped_column(Integer, nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=True)
