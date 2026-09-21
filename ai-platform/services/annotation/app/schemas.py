import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabelClassIn(BaseModel):
    class_name: str
    color: str | None = None
    display_order: int | None = None


class LabelClassOut(LabelClassIn):
    model_config = ConfigDict(from_attributes=True)
    class_id: int
    schema_id: uuid.UUID


class LabelSchemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    schema_id: uuid.UUID
    dataset_id: uuid.UUID
    classes: list[LabelClassOut] = []


class AnnotationIn(BaseModel):
    class_id: int
    shape_type: str = Field(pattern="^(bbox|polygon)$")
    bbox_x: float | None = None
    bbox_y: float | None = None
    bbox_w: float | None = None
    bbox_h: float | None = None
    polygon_points: str | None = None  # JSON-encoded [[x,y], ...]


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    annotation_id: uuid.UUID
    asset_id: uuid.UUID
    class_id: int | None
    bbox_x: float | None
    bbox_y: float | None
    bbox_w: float | None
    bbox_h: float | None
    shape_type: str | None
    polygon_points: str | None
    source: str
    confidence: float | None
    risk_score: float | None
    review_status: str
    reviewed_by: str | None
    annotated_by: str | None
    updated_at: datetime | None


class AISuggestionIn(BaseModel):
    class_id: int
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    confidence: float
    annotated_by: str = "bootstrap-model"


class ReviewDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


class DemoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    demo_id: uuid.UUID
    dataset_id: uuid.UUID
    class_id: int | None
    demo_image_path: str | None
    demo_image_url: str | None = None
    demo_annotation_json: str | None
    text_description: str | None
    created_by: str | None
    created_at: datetime | None


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(yolo|coco)$")
