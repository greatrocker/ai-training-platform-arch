import httpx

from .config import settings


def get_schema(dataset_id: str) -> dict:
    resp = httpx.get(f"{settings.annotation_service_url}/api/annotation/schema/{dataset_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def export_yolo(dataset_id: str, format: str = "yolo") -> dict:
    # Export downloads every asset's raw image from MinIO, zips them, and
    # re-uploads — synchronous and I/O bound, so a dataset with hundreds of
    # large (multi-thousand-pixel) images can legitimately take minutes.
    resp = httpx.post(
        f"{settings.annotation_service_url}/api/annotation/export/{dataset_id}",
        params={"format": format},
        timeout=900,
    )
    resp.raise_for_status()
    return resp.json()


def list_annotations(asset_id: str) -> list[dict]:
    resp = httpx.get(f"{settings.annotation_service_url}/api/annotation/assets/{asset_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def labeled_status(asset_ids: list[str]) -> dict[str, bool]:
    if not asset_ids:
        return {}
    resp = httpx.get(
        f"{settings.annotation_service_url}/api/annotation/labeled-status",
        params={"asset_ids": ",".join(asset_ids)},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def submit_suggestion(
    asset_id: str, class_id: int, bbox_x: float, bbox_y: float, bbox_w: float, bbox_h: float, confidence: float
) -> dict:
    resp = httpx.post(
        f"{settings.annotation_service_url}/api/annotation/assets/{asset_id}/suggestions",
        json={
            "class_id": class_id,
            "bbox_x": bbox_x,
            "bbox_y": bbox_y,
            "bbox_w": bbox_w,
            "bbox_h": bbox_h,
            "confidence": confidence,
            "annotated_by": "bootstrap-model",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
