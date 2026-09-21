import json
import tempfile
import uuid
from pathlib import Path

from celery import Celery

from . import dataset_client
from .config import settings
from .db import SessionLocal
from .models import Annotation, AnnotationDemo
from .risk import compute_risk_score
from .storage import download_file
from .vlm_client import VLMNotConfigured, suggest as vlm_suggest

celery_app = Celery("annotation", broker=settings.celery_broker_url, backend=settings.celery_broker_url)


@celery_app.task(name="annotation.suggest_asset")
def suggest_asset(asset_id: str, dataset_id: str, class_id: int, text_description: str) -> dict:
    db = SessionLocal()
    try:
        demos = (
            db.query(AnnotationDemo)
            .filter(AnnotationDemo.dataset_id == uuid.UUID(dataset_id), AnnotationDemo.class_id == class_id)
            .all()
        )
        demo_boxes = [json.loads(d.demo_annotation_json) for d in demos if d.demo_annotation_json]

        asset = dataset_client.get_asset(asset_id)

        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "image.jpg"
            download_file(asset["minio_path"], str(local_path))
            image_bytes = local_path.read_bytes()

        try:
            result = vlm_suggest(image_bytes, demo_boxes, text_description)
        except VLMNotConfigured as exc:
            return {"asset_id": asset_id, "status": "skipped", "reason": str(exc)}

        risk_score = compute_risk_score(
            confidence=result["confidence"],
            suggested=result,
            demo_boxes=demo_boxes,
            img_w=asset["width"],
            img_h=asset["height"],
        )
        review_status = (
            "pending_review"
            if result["confidence"] < settings.annotation_ai_confidence_threshold
            or risk_score > settings.annotation_risk_score_threshold
            else "pending_review"  # AI suggestions never auto-finalize, see doc 3.1 point 1
        )

        db.add(
            Annotation(
                asset_id=uuid.UUID(asset_id),
                class_id=class_id,
                bbox_x=result["bbox_x"],
                bbox_y=result["bbox_y"],
                bbox_w=result["bbox_w"],
                bbox_h=result["bbox_h"],
                shape_type="bbox",
                source="ai_suggested",
                confidence=result["confidence"],
                risk_score=risk_score,
                review_status=review_status,
                annotated_by="vlm",
            )
        )
        db.commit()
        return {"asset_id": asset_id, "status": "suggested", "risk_score": risk_score}
    except Exception as exc:
        db.rollback()
        return {"asset_id": asset_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
