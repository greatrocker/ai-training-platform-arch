import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import dataset_client, models
from ..config import settings
from ..db import get_db
from ..worker import suggest_asset

router = APIRouter(prefix="/api/annotation/suggest", tags=["suggest"])


@router.post("/{dataset_id}")
def trigger_suggest(dataset_id: uuid.UUID, class_id: int, text_description: str = "", db: Session = Depends(get_db)):
    assets = dataset_client.list_dataset_assets(str(dataset_id))

    already_suggested = {
        row.asset_id
        for row in db.query(models.Annotation.asset_id)
        .filter(models.Annotation.class_id == class_id, models.Annotation.source == "ai_suggested")
        .all()
    }

    queued = 0
    for asset in assets:
        asset_id = uuid.UUID(asset["asset_id"])
        if asset_id in already_suggested:
            continue
        suggest_asset.delay(str(asset_id), str(dataset_id), class_id, text_description)
        queued += 1

    result = {"queued": queued, "total_assets": len(assets)}
    if not settings.annotation_vlm_endpoint:
        result["warning"] = (
            "ANNOTATION_VLM_ENDPOINT is not configured — queued tasks will each "
            "resolve as 'skipped' until a VLM backend is wired up (see vlm_client.py)."
        )
    return result
