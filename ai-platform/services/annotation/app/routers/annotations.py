import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/annotation", tags=["annotations"])


@router.get("/assets/{asset_id}", response_model=list[schemas.AnnotationOut])
def list_annotations(asset_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.Annotation)
        .filter(models.Annotation.asset_id == asset_id)
        .order_by(models.Annotation.updated_at.desc())
        .all()
    )


@router.get("/labeled-status")
def labeled_status(asset_ids: str, db: Session = Depends(get_db)):
    """Bulk check which of the given asset_ids already have at least one
    annotation (any status) — used by training-service's bootstrap-label
    task to skip images that are already labeled or awaiting review."""
    ids = [uuid.UUID(a) for a in asset_ids.split(",") if a]
    rows = (
        db.query(models.Annotation.asset_id)
        .filter(models.Annotation.asset_id.in_(ids))
        .distinct()
        .all()
    )
    labeled = {str(r.asset_id) for r in rows}
    return {str(i): (str(i) in labeled) for i in ids}


@router.post("/assets/{asset_id}/suggestions", response_model=schemas.AnnotationOut, status_code=201)
def create_ai_suggestion(asset_id: uuid.UUID, payload: schemas.AISuggestionIn, db: Session = Depends(get_db)):
    """Used by training-service's bootstrap-label task (a detector trained
    on the dataset's own current annotations, not the VLM/demo path in
    vlm_client.py). Always lands in pending_review — same rule as VLM
    suggestions: an AI-produced box never counts as final on its own."""
    annotation = models.Annotation(
        asset_id=asset_id,
        class_id=payload.class_id,
        bbox_x=payload.bbox_x,
        bbox_y=payload.bbox_y,
        bbox_w=payload.bbox_w,
        bbox_h=payload.bbox_h,
        shape_type="bbox",
        source="ai_suggested",
        confidence=payload.confidence,
        risk_score=round(1.0 - payload.confidence, 4),
        review_status="pending_review",
        annotated_by=payload.annotated_by,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.post("/assets/{asset_id}", response_model=schemas.AnnotationOut, status_code=201)
def create_annotation(
    asset_id: uuid.UUID,
    payload: schemas.AnnotationIn,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
):
    annotation = models.Annotation(
        asset_id=asset_id,
        source="human",
        review_status="final",
        annotated_by=x_user_id or "unknown",
        updated_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.put("/{annotation_id}", response_model=schemas.AnnotationOut)
def update_annotation(
    annotation_id: uuid.UUID,
    payload: schemas.AnnotationIn,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
):
    annotation = db.get(models.Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="annotation not found")
    for key, value in payload.model_dump().items():
        setattr(annotation, key, value)
    annotation.updated_at = datetime.now(timezone.utc)
    annotation.annotated_by = x_user_id or annotation.annotated_by
    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/{annotation_id}", status_code=204)
def delete_annotation(annotation_id: uuid.UUID, db: Session = Depends(get_db)):
    annotation = db.get(models.Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="annotation not found")
    db.delete(annotation)
    db.commit()


@router.get("/review-queue", response_model=list[schemas.AnnotationOut])
def review_queue(dataset_asset_ids: str | None = Query(default=None), db: Session = Depends(get_db)):
    """List AI-suggested annotations awaiting review, highest risk first.

    dataset_asset_ids: optional comma-separated asset_id filter (the caller
    resolves which assets belong to a dataset via dataset-service, since
    annotation-service does not know about datasets directly).
    """
    query = db.query(models.Annotation).filter(models.Annotation.review_status == "pending_review")
    if dataset_asset_ids:
        ids = [uuid.UUID(a) for a in dataset_asset_ids.split(",") if a]
        query = query.filter(models.Annotation.asset_id.in_(ids))
    return query.order_by(models.Annotation.risk_score.desc()).all()


@router.post("/{annotation_id}/review", response_model=schemas.AnnotationOut)
def review_annotation(
    annotation_id: uuid.UUID,
    payload: schemas.ReviewDecision,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
):
    annotation = db.get(models.Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="annotation not found")
    if annotation.review_status != "pending_review":
        raise HTTPException(status_code=409, detail="annotation is not awaiting review")

    annotation.review_status = "final" if payload.decision == "approved" else "rejected"
    annotation.reviewed_by = x_user_id or "unknown"
    annotation.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(annotation)
    return annotation
