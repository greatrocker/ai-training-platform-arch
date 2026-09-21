"""Real Page4 training: detect and segment, YOLO26 family only for now
(other architectures/tasks are a later addition per product decision).

training_mode:
  full        - start from the model_registry's pretrained weights.
  incremental - start from a parent job's own trained weights
                (parent_job_id lineage), then keep training on whatever the
                dataset's annotations look like now. replay_ratio (mixing
                in a sample of the parent's original data to fight
                catastrophic forgetting) is not implemented yet — today's
                incremental mode is a straight continued fine-tune.
"""

import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from ultralytics import YOLO

from .config import settings
from .data_prep import class_index_map, download_and_extract, has_any_label
from .db import SessionLocal
from .models import ModelRegistry, TrainingJob
from .storage import download_model_weights, upload_model_weights

# Freeze the backbone + neck, leaving only the task head trainable — a
# reasonable default for "fine-tune on top of what it already knows"
# without needing per-architecture layer counts.
FREEZE_LAYERS = 10


def _resolve_device(device: str) -> str:
    if device == "auto":
        return settings.training_gpu_device
    return device


def _make_progress_callback(db, job: TrainingJob):
    def _on_epoch_end(trainer) -> None:
        try:
            job.progress_current_epoch = int(getattr(trainer, "epoch", 0)) + 1
            job.progress_total_epochs = int(getattr(trainer, "epochs", 0)) or None
            db.commit()
        except Exception:
            db.rollback()

    return _on_epoch_end


def run_training_job(job_id: str) -> dict:
    db = SessionLocal()
    try:
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job is None:
            return {"status": "not_found"}

        params = json.loads(job.params_json)
        registry = db.get(ModelRegistry, job.model_key)
        if registry is None:
            raise ValueError(f"model_key {job.model_key} not found in model_registry")

        export_format = "yolo-seg" if registry.task_type == "segment" else "yolo"

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            extract_dir = download_and_extract(str(job.dataset_id), export_format, tmp_path)

            labels_dir = extract_dir / "labels"
            if not labels_dir.exists() or not has_any_label(labels_dir):
                raise ValueError("dataset has no approved annotations to train on")

            _, _, names = class_index_map(str(job.dataset_id))
            data_yaml = extract_dir / "data.yaml"
            data_yaml.write_text(
                yaml.safe_dump(
                    {
                        "path": str(extract_dir),
                        "train": "images",
                        "val": "images",
                        "names": {i: n for i, n in enumerate(names)},
                    }
                )
            )

            if job.training_mode == "incremental" and job.parent_job_id:
                parent = db.get(TrainingJob, job.parent_job_id)
                if parent is None or not parent.output_model_path:
                    raise ValueError("parent_job_id has no usable output_model_path")
                base_weights = tmp_path / "parent.pt"
                download_model_weights(parent.output_model_path, str(base_weights))
                weights_source = str(base_weights)
            else:
                weights_source = registry.base_weight_path or f"{job.model_key}.pt"

            model = YOLO(weights_source)
            model.add_callback("on_train_epoch_end", _make_progress_callback(db, job))
            runs_dir = tmp_path / "runs"
            train_kwargs = dict(
                data=str(data_yaml),
                epochs=params["epochs"],
                imgsz=params["img_size"],
                batch=params["batch_size"],
                lr0=params["learning_rate"],
                optimizer=params["optimizer"],
                device=_resolve_device(params["device"]),
                pretrained=params["pretrained"],
                patience=params.get("patience", 30),
                project=str(runs_dir),
                name="job",
                exist_ok=True,
                verbose=False,
                workers=0,  # required under Celery's --pool=solo, see docker-compose.yml
            )
            if params.get("freeze_backbone"):
                train_kwargs["freeze"] = FREEZE_LAYERS

            results = model.train(**train_kwargs)
            metrics = dict(getattr(results, "results_dict", {}) or {})

            best_weights = runs_dir / "job" / "weights" / "best.pt"
            if not best_weights.exists():
                raise RuntimeError("training did not produce weights")

            object_name = f"{job.job_id}/best.pt"
            upload_model_weights(object_name, str(best_weights))

            job.status = "completed"
            job.output_model_path = object_name
            job.metrics_json = json.dumps(metrics)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "completed", "output_model_path": object_name, "metrics": metrics}

    except Exception as exc:
        db.rollback()
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job is not None:
            job.status = "failed"
            job.metrics_json = json.dumps({"error": str(exc)})
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        return {"status": "failed", "reason": str(exc)}
    finally:
        db.close()
