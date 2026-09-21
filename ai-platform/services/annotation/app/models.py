import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Annotation(Base):
    __tablename__ = "annotation"
    annotation_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER)  # cross-service ref, no FK
    class_id: Mapped[int] = mapped_column(Integer, nullable=True)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=True)
    bbox_w: Mapped[float] = mapped_column(Float, nullable=True)
    bbox_h: Mapped[float] = mapped_column(Float, nullable=True)
    shape_type: Mapped[str] = mapped_column(String(20), nullable=True)  # bbox/polygon
    polygon_points: Mapped[str] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="human")
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="final")
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(nullable=True)
    annotated_by: Mapped[str] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(nullable=True)


class LabelSchema(Base):
    __tablename__ = "label_schema"
    schema_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, unique=True)  # cross-service ref
    created_at: Mapped[datetime] = mapped_column(nullable=True)


class LabelClass(Base):
    __tablename__ = "label_class"
    class_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, ForeignKey("label_schema.schema_id"))
    class_name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(20), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=True)


class AnnotationDemo(Base):
    __tablename__ = "annotation_demo"
    demo_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UNIQUEIDENTIFIER)  # cross-service ref, no FK
    class_id: Mapped[int] = mapped_column(Integer, nullable=True)
    demo_image_path: Mapped[str] = mapped_column(String(500), nullable=True)
    demo_annotation_json: Mapped[str] = mapped_column(String, nullable=True)
    text_description: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=True)
