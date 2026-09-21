import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import ModelRegistry, TrainingJob
from ..storage import presigned_model_url
from ..worker import run_job

router = APIRouter(prefix="/api/training", tags=["training-jobs"])


@router.get("/models", response_model=list[schemas.ModelRegistryOut])
def list_models(task_type: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(ModelRegistry).filter(ModelRegistry.is_active == True)  # noqa: E712 (MSSQL BIT needs `= 1`, not `IS`)
    if task_type:
        query = query.filter(ModelRegistry.task_type == task_type)
    return query.order_by(ModelRegistry.display_order.asc()).all()


@router.post("/jobs", response_model=schemas.TrainingJobOut, status_code=201)
def create_job(payload: schemas.TrainingJobIn, db: Session = Depends(get_db)):
    registry = db.get(ModelRegistry, payload.model_key)
    if registry is None or not registry.is_active:
        raise HTTPException(status_code=400, detail=f"unknown or inactive model_key: {payload.model_key}")

    if payload.training_mode == "incremental":
        if payload.base_job_id is None:
            raise HTTPException(status_code=400, detail="base_job_id is required for incremental training")
        base_job = db.get(TrainingJob, payload.base_job_id)
        if base_job is None or base_job.status != "completed":
            raise HTTPException(status_code=400, detail="base_job_id must reference a completed training job")

    params = {
        "epochs": payload.epochs,
        "batch_size": payload.batch_size,
        "img_size": payload.img_size,
        "learning_rate": payload.learning_rate,
        "optimizer": payload.optimizer,
        "pretrained": payload.pretrained,
        "device": payload.device,
        "freeze_backbone": payload.freeze_backbone,
        "patience": payload.patience,
    }

    job = TrainingJob(
        dataset_id=payload.dataset_id,
        model_key=payload.model_key,
        params_json=json.dumps(params),
        status="queued",
        training_mode=payload.training_mode,
        parent_job_id=payload.base_job_id,
        freeze_backbone=payload.freeze_backbone,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    run_job.delay(str(job.job_id))
    return job


@router.get("/jobs", response_model=list[schemas.TrainingJobOut])
def list_jobs(
    dataset_id: uuid.UUID | None = Query(default=None),
    model_key: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(TrainingJob)
    if dataset_id:
        query = query.filter(TrainingJob.dataset_id == dataset_id)
    if model_key:
        query = query.filter(TrainingJob.model_key == model_key)
    return query.order_by(TrainingJob.started_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=schemas.TrainingJobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(TrainingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/jobs/{job_id}/download")
def download_job_weights(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(TrainingJob, job_id)
    if job is None or not job.output_model_path:
        raise HTTPException(status_code=404, detail="job has no output weights")
    return {"download_url": presigned_model_url(job.output_model_path)}


def _ready_job_and_registry(job_id: uuid.UUID, db: Session) -> tuple[TrainingJob, ModelRegistry]:
    job = db.get(TrainingJob, job_id)
    if job is None or job.status != "completed" or not job.output_model_path:
        raise HTTPException(status_code=400, detail="job is not a completed training run with output weights")
    registry = db.get(ModelRegistry, job.model_key)
    if registry is None:
        raise HTTPException(status_code=400, detail=f"model_key {job.model_key} not found in model_registry")
    return job, registry


@router.post("/jobs/{job_id}/predict-asset")
def predict_asset(
    job_id: uuid.UUID,
    asset_id: uuid.UUID,
    conf: float | None = Query(default=None, ge=0, le=1),
    db: Session = Depends(get_db),
):
    from ..predict import predict_on_asset

    job, registry = _ready_job_and_registry(job_id, db)
    try:
        return predict_on_asset(job, registry, str(asset_id), conf=conf)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"inference failed: {exc}") from exc


@router.post("/jobs/{job_id}/predict-upload")
async def predict_upload(
    job_id: uuid.UUID,
    image: UploadFile = File(...),
    conf: float | None = Query(default=None, ge=0, le=1),
    db: Session = Depends(get_db),
):
    from ..predict import predict_on_upload

    job, registry = _ready_job_and_registry(job_id, db)
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image must be an image/* upload")
    try:
        return predict_on_upload(job, registry, await image.read(), conf=conf)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"inference failed: {exc}") from exc
