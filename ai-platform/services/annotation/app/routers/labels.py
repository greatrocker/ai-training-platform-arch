import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/annotation/schema", tags=["labels"])


def _get_or_create_schema(dataset_id: uuid.UUID, db: Session) -> models.LabelSchema:
    schema = db.query(models.LabelSchema).filter_by(dataset_id=dataset_id).first()
    if schema:
        return schema
    schema = models.LabelSchema(dataset_id=dataset_id)
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


@router.get("/{dataset_id}", response_model=schemas.LabelSchemaOut)
def get_schema(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    schema = _get_or_create_schema(dataset_id, db)
    classes = (
        db.query(models.LabelClass)
        .filter_by(schema_id=schema.schema_id)
        .order_by(models.LabelClass.display_order.asc())
        .all()
    )
    out = schemas.LabelSchemaOut.model_validate(schema)
    out.classes = [schemas.LabelClassOut.model_validate(c) for c in classes]
    return out


@router.post("/{dataset_id}/classes", response_model=schemas.LabelClassOut, status_code=201)
def add_class(dataset_id: uuid.UUID, payload: schemas.LabelClassIn, db: Session = Depends(get_db)):
    schema = _get_or_create_schema(dataset_id, db)
    label_class = models.LabelClass(schema_id=schema.schema_id, **payload.model_dump())
    db.add(label_class)
    db.commit()
    db.refresh(label_class)
    return label_class


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: int, db: Session = Depends(get_db)):
    label_class = db.get(models.LabelClass, class_id)
    if not label_class:
        raise HTTPException(status_code=404, detail="class not found")
    db.delete(label_class)
    db.commit()
