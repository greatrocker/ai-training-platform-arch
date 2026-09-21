"""Run a completed training_job's weights on a single image — either an
existing dataset asset (so the frontend can show the human annotation next
to the prediction) or an arbitrary uploaded image. No CCTV/RTSP involved;
this is purely "throw an image at the model and see what it says".
"""

import base64
import json
import tempfile
from pathlib import Path

from ultralytics import YOLO

from . import annotation_client, dataset_client
from .data_prep import class_index_map
from .models import ModelRegistry, TrainingJob
from .storage import download_file, download_model_weights

_model_cache: dict[str, YOLO] = {}
DEFAULT_CONF = 0.25  # ultralytics' own predict() default — made explicit/overridable here


def _load_model(job: TrainingJob) -> YOLO:
    key = str(job.job_id)
    if key not in _model_cache:
        with tempfile.TemporaryDirectory() as tmp:
            weights_path = Path(tmp) / "best.pt"
            download_model_weights(job.output_model_path, str(weights_path))
            _model_cache[key] = YOLO(str(weights_path))
    return _model_cache[key]


def _results_to_predictions(results, index_to_id: dict[int, int], is_segment: bool) -> list[dict]:
    predictions = []
    boxes = results[0].boxes
    masks = results[0].masks if is_segment else None

    for i, box in enumerate(boxes):
        cls_index = int(box.cls[0])
        if cls_index not in index_to_id:
            continue
        confidence = float(box.conf[0])
        entry = {"class_id": index_to_id[cls_index], "confidence": round(confidence, 4)}

        if is_segment and masks is not None:
            points = masks.xy[i].tolist()
            entry["shape_type"] = "polygon"
            entry["polygon_points"] = points
        else:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            entry["shape_type"] = "bbox"
            entry["bbox_x"] = x1
            entry["bbox_y"] = y1
            entry["bbox_w"] = x2 - x1
            entry["bbox_h"] = y2 - y1
        predictions.append(entry)
    return predictions


def _job_img_size(job: TrainingJob) -> int:
    try:
        return int(json.loads(job.params_json).get("img_size", 640))
    except (TypeError, ValueError):
        return 640


def predict_on_asset(job: TrainingJob, registry: ModelRegistry, asset_id: str, conf: float | None = None) -> dict:
    _, index_to_id, _ = class_index_map(str(job.dataset_id))
    asset = dataset_client.get_asset(asset_id)
    model = _load_model(job)
    conf_used = conf if conf is not None else DEFAULT_CONF
    img_size = _job_img_size(job)

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / "image.jpg"
        download_file(asset["minio_path"], str(local_path))
        # imgsz matches what the model was actually trained at — predicting
        # at a different size than training silently shifts feature scale
        # and hurts accuracy, so this must not be left to ultralytics' own
        # default.
        results = model.predict(str(local_path), imgsz=img_size, conf=conf_used, verbose=False)

    predictions = _results_to_predictions(results, index_to_id, registry.task_type == "segment")
    ground_truth = annotation_client.list_annotations(asset_id)
    return {
        "asset_id": asset_id,
        "width": asset["width"],
        "height": asset["height"],
        "predictions": predictions,
        "ground_truth": ground_truth,
        "conf_used": conf_used,
        "imgsz_used": img_size,
    }


def predict_on_upload(job: TrainingJob, registry: ModelRegistry, image_bytes: bytes, conf: float | None = None) -> dict:
    _, index_to_id, _ = class_index_map(str(job.dataset_id))
    model = _load_model(job)
    conf_used = conf if conf is not None else DEFAULT_CONF
    img_size = _job_img_size(job)

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / "upload.jpg"
        local_path.write_bytes(image_bytes)
        results = model.predict(str(local_path), imgsz=img_size, conf=conf_used, verbose=False)
        width, height = results[0].orig_shape[1], results[0].orig_shape[0]

    predictions = _results_to_predictions(results, index_to_id, registry.task_type == "segment")
    return {
        "width": width,
        "height": height,
        "image_base64": base64.b64encode(image_bytes).decode(),
        "predictions": predictions,
        "conf_used": conf_used,
        "imgsz_used": img_size,
    }
