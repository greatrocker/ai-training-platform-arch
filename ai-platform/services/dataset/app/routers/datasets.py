import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..db import get_db
from ..storage import presigned_url
from ..windows_path import InvalidWindowsPath, resolve_windows_path
from ..worker import ingest_dataset

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


def _validate_source_path(source_path: str) -> None:
    try:
        resolved = resolve_windows_path(source_path, settings.mounted_drive_set)
    except InvalidWindowsPath as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not resolved.exists():
        raise HTTPException(
            status_code=400,
            detail=f"path not found: {source_path} (looked for it at {resolved} inside the container)",
        )


@router.get("", response_model=list[schemas.DatasetOut])
def list_datasets(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(
        models.Dataset,
        func.count(models.DatasetAsset.asset_id).label("asset_count"),
    ).outerjoin(models.DatasetAsset, models.DatasetAsset.dataset_id == models.Dataset.dataset_id)

    if status:
        query = query.filter(models.Dataset.status == status)

    query = query.group_by(*[c for c in models.Dataset.__table__.columns])

    results = []
    for dataset, asset_count in query.all():
        out = schemas.DatasetOut.model_validate(dataset)
        out.asset_count = asset_count
        results.append(out)
    return results


@router.post("", response_model=schemas.DatasetOut, status_code=201)
def create_dataset(
    payload: schemas.DatasetIn,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
):
    _validate_source_path(payload.source_path)

    dataset = models.Dataset(
        name=payload.name,
        source_path=payload.source_path,
        source_type=payload.source_type,
        filename_pattern=payload.filename_pattern,
        status="pending",
        created_by=x_user_id or "unknown",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    ingest_dataset.delay(str(dataset.dataset_id))

    out = schemas.DatasetOut.model_validate(dataset)
    out.asset_count = 0
    return out


@router.get("/assets/{asset_id}", response_model=schemas.DatasetAssetOut)
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)):
    asset = db.get(models.DatasetAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    out = schemas.DatasetAssetOut.model_validate(asset)
    if asset.minio_path:
        thumb_object = asset.minio_path.replace("/raw/", "/thumbs/", 1)
        out.thumb_url = presigned_url(thumb_object)
        out.raw_url = presigned_url(asset.minio_path)
    return out


@router.get("/{dataset_id}", response_model=schemas.DatasetOut)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")
    asset_count = db.query(func.count(models.DatasetAsset.asset_id)).filter(
        models.DatasetAsset.dataset_id == dataset_id
    ).scalar()
    out = schemas.DatasetOut.model_validate(dataset)
    out.asset_count = asset_count or 0
    return out


@router.get("/{dataset_id}/assets", response_model=list[schemas.DatasetAssetOut])
def list_assets(
    dataset_id: uuid.UUID,
    limit: int = Query(default=60, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")

    assets = (
        db.query(models.DatasetAsset)
        .filter(models.DatasetAsset.dataset_id == dataset_id)
        .order_by(models.DatasetAsset.frame_index.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for asset in assets:
        out = schemas.DatasetAssetOut.model_validate(asset)
        if asset.minio_path:
            thumb_object = asset.minio_path.replace("/raw/", "/thumbs/", 1)
            out.thumb_url = presigned_url(thumb_object)
            out.raw_url = presigned_url(asset.minio_path)
        results.append(out)
    return results


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    dataset = db.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")
    db.query(models.DatasetAsset).filter(models.DatasetAsset.dataset_id == dataset_id).delete()
    db.delete(dataset)
    db.commit()
