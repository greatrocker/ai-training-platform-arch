import json
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import dataset_client, models
from ..db import get_db
from ..storage import download_file, presigned_download_url, upload_file
from .labels import _get_or_create_schema

router = APIRouter(prefix="/api/annotation/export", tags=["export"])


def _polygon_points(ann: "models.Annotation") -> list[tuple[float, float]]:
    """Points for YOLO-seg export. Polygon annotations use their drawn
    points as-is; bbox annotations fall back to their 4 corners as a
    rectangle — lets a dataset annotated with plain boxes still train a
    -seg model, just with box-shaped masks until polygons are drawn."""
    if ann.shape_type == "polygon" and ann.polygon_points:
        return [(p[0], p[1]) for p in json.loads(ann.polygon_points)]
    if ann.shape_type == "bbox":
        x, y, w, h = ann.bbox_x, ann.bbox_y, ann.bbox_w, ann.bbox_h
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return []


@router.post("/{dataset_id}")
def export_dataset(dataset_id: uuid.UUID, format: str, db: Session = Depends(get_db)):
    if format not in ("yolo", "yolo-seg", "coco"):
        raise HTTPException(status_code=400, detail="format must be yolo, yolo-seg, or coco")

    schema = _get_or_create_schema(dataset_id, db)
    classes = (
        db.query(models.LabelClass)
        .filter_by(schema_id=schema.schema_id)
        .order_by(models.LabelClass.class_id.asc())
        .all()
    )
    if not classes:
        raise HTTPException(status_code=400, detail="no label classes defined for this dataset yet")
    class_index = {c.class_id: i for i, c in enumerate(classes)}

    assets = dataset_client.list_dataset_assets(str(dataset_id))
    if not assets:
        raise HTTPException(status_code=400, detail="dataset has no assets")

    export_id = uuid.uuid4()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        images_dir_local = images_dir

        coco_images, coco_annotations = [], []
        labels_dir = tmp_path / "labels"
        if format in ("yolo", "yolo-seg"):
            labels_dir.mkdir()

        for img_index, asset in enumerate(assets):
            asset_id = uuid.UUID(asset["asset_id"])
            filename = f"{asset_id}.jpg"
            download_file(asset["minio_path"], str(images_dir_local / filename))

            annotations = (
                db.query(models.Annotation)
                .filter(models.Annotation.asset_id == asset_id, models.Annotation.review_status == "final")
                .all()
            )

            if format == "yolo":
                lines = []
                for ann in annotations:
                    if ann.class_id not in class_index or ann.shape_type != "bbox":
                        continue
                    cx = (ann.bbox_x + ann.bbox_w / 2) / asset["width"]
                    cy = (ann.bbox_y + ann.bbox_h / 2) / asset["height"]
                    w = ann.bbox_w / asset["width"]
                    h = ann.bbox_h / asset["height"]
                    lines.append(f"{class_index[ann.class_id]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                (labels_dir / f"{asset_id}.txt").write_text("\n".join(lines))
            elif format == "yolo-seg":
                lines = []
                for ann in annotations:
                    if ann.class_id not in class_index:
                        continue
                    points = _polygon_points(ann)
                    if len(points) < 3:
                        continue
                    coords = " ".join(
                        f"{px / asset['width']:.6f} {py / asset['height']:.6f}" for px, py in points
                    )
                    lines.append(f"{class_index[ann.class_id]} {coords}")
                (labels_dir / f"{asset_id}.txt").write_text("\n".join(lines))
            else:
                coco_images.append(
                    {"id": img_index, "file_name": filename, "width": asset["width"], "height": asset["height"]}
                )
                for ann in annotations:
                    if ann.class_id not in class_index or ann.shape_type != "bbox":
                        continue
                    coco_annotations.append(
                        {
                            "id": len(coco_annotations),
                            "image_id": img_index,
                            "category_id": class_index[ann.class_id],
                            "bbox": [ann.bbox_x, ann.bbox_y, ann.bbox_w, ann.bbox_h],
                            "area": ann.bbox_w * ann.bbox_h,
                            "iscrowd": 0,
                        }
                    )

        if format in ("yolo", "yolo-seg"):
            (tmp_path / "classes.txt").write_text("\n".join(c.class_name for c in classes))
        else:
            coco = {
                "images": coco_images,
                "annotations": coco_annotations,
                "categories": [{"id": i, "name": c.class_name} for i, c in enumerate(classes)],
            }
            (tmp_path / "annotations.json").write_text(json.dumps(coco, ensure_ascii=False))

        zip_path = tmp_path / f"{export_id}.zip"
        # ZIP_STORED, not DEFLATED: the payload is almost entirely already-
        # compressed JPEGs, so re-deflating them burns CPU/time for near-zero
        # size benefit — this matters once datasets have hundreds of large images.
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            for path in tmp_path.rglob("*"):
                if path.is_file() and path != zip_path:
                    zf.write(path, path.relative_to(tmp_path))

        object_name = f"{dataset_id}/exports/{export_id}.zip"
        upload_file(object_name, str(zip_path), content_type="application/zip")

    download_url = presigned_download_url(object_name)
    return {"export_id": str(export_id), "object_name": object_name, "download_url": download_url}
