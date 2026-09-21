import json
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..storage import presigned_download_url, upload_file

router = APIRouter(prefix="/api/annotation/demos", tags=["demos"])


@router.get("", response_model=list[schemas.DemoOut])
def list_demos(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    demos = db.query(models.AnnotationDemo).filter(models.AnnotationDemo.dataset_id == dataset_id).all()
    results = []
    for demo in demos:
        out = schemas.DemoOut.model_validate(demo)
        if demo.demo_image_path:
            out.demo_image_url = presigned_download_url(demo.demo_image_path)
        results.append(out)
    return results


@router.post("", response_model=schemas.DemoOut, status_code=201)
async def create_demo(
    dataset_id: uuid.UUID = Form(...),
    class_id: int = Form(...),
    bbox_x: float = Form(...),
    bbox_y: float = Form(...),
    bbox_w: float = Form(...),
    bbox_h: float = Form(...),
    text_description: str = Form(default=""),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image must be an image/* upload")

    demo_id = uuid.uuid4()
    object_name = f"{dataset_id}/demos/{demo_id}.jpg"

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / "demo.jpg"
        local_path.write_bytes(await image.read())
        upload_file(object_name, str(local_path), content_type="image/jpeg")

    demo = models.AnnotationDemo(
        demo_id=demo_id,
        dataset_id=dataset_id,
        class_id=class_id,
        demo_image_path=object_name,
        demo_annotation_json=json.dumps(
            {"bbox_x": bbox_x, "bbox_y": bbox_y, "bbox_w": bbox_w, "bbox_h": bbox_h}
        ),
        text_description=text_description,
    )
    db.add(demo)
    db.commit()
    db.refresh(demo)
    out = schemas.DemoOut.model_validate(demo)
    out.demo_image_url = presigned_download_url(object_name)
    return out


@router.delete("/{demo_id}", status_code=204)
def delete_demo(demo_id: uuid.UUID, db: Session = Depends(get_db)):
    demo = db.get(models.AnnotationDemo, demo_id)
    if not demo:
        raise HTTPException(status_code=404, detail="demo not found")
    db.delete(demo)
    db.commit()
