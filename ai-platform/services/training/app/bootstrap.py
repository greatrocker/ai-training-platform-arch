"""Semi-automatic ("bootstrap") labeling: train a small YOLO26 model on
whatever annotations already exist for a dataset, then run it over the
still-unlabeled images and submit the detections back to annotation-service
as ai_suggested/pending_review boxes for human review.

Re-running this after reviewing/approving more boxes retrains on the now
larger approved set and only touches images that still have zero
annotations — that's what makes it incremental: each round's approved
labels feed the next round's training data.

Detect-only for now (bbox suggestions) — a segmentation-mask version of
this same flow can reuse data_prep's "yolo-seg" export when it's needed.
"""

import tempfile
from pathlib import Path

import yaml
from ultralytics import YOLO

from . import annotation_client, dataset_client
from .config import settings
from .data_prep import class_index_map, download_and_extract, has_any_label
from .storage import download_file


def _make_progress_callback(task):
    def _on_epoch_end(trainer) -> None:
        if task is None:
            return
        try:
            task.update_state(
                state="PROGRESS",
                meta={
                    "phase": "training",
                    "current_epoch": int(getattr(trainer, "epoch", 0)) + 1,
                    "total_epochs": int(getattr(trainer, "epochs", 0)) or None,
                },
            )
        except Exception:
            pass

    return _on_epoch_end


def run_bootstrap_label(dataset_id: str, conf_threshold: float | None = None, task=None) -> dict:
    conf = conf_threshold if conf_threshold is not None else settings.bootstrap_conf_threshold
    _, index_to_id, names = class_index_map(dataset_id)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        extract_dir = download_and_extract(dataset_id, "yolo", tmp_path)

        labels_dir = extract_dir / "labels"
        if not labels_dir.exists() or not has_any_label(labels_dir):
            return {"status": "skipped", "reason": "no approved annotations yet to train from"}

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

        runs_dir = tmp_path / "runs"
        model = YOLO("yolo26n.pt")
        model.add_callback("on_train_epoch_end", _make_progress_callback(task))
        model.train(
            data=str(data_yaml),
            epochs=settings.bootstrap_epochs,
            imgsz=settings.bootstrap_img_size,
            device=settings.training_gpu_device,
            project=str(runs_dir),
            name="bootstrap",
            exist_ok=True,
            verbose=False,
            patience=0,
            workers=0,  # no DataLoader subprocesses — see --pool=solo note in docker-compose.yml
        )
        best_weights = runs_dir / "bootstrap" / "weights" / "best.pt"
        if not best_weights.exists():
            return {"status": "failed", "reason": "training did not produce weights"}

        inference_model = YOLO(str(best_weights))

        all_assets = dataset_client.list_dataset_assets(dataset_id)
        asset_ids = [a["asset_id"] for a in all_assets]
        labeled = annotation_client.labeled_status(asset_ids)
        unlabeled = [a for a in all_assets if not labeled.get(a["asset_id"], False)]

        suggestions_created = 0
        images_dir = tmp_path / "infer"
        images_dir.mkdir()

        for scan_index, asset in enumerate(unlabeled, start=1):
            if task is not None:
                try:
                    task.update_state(
                        state="PROGRESS",
                        meta={"phase": "scanning", "current_image": scan_index, "total_images": len(unlabeled)},
                    )
                except Exception:
                    pass
            local_path = images_dir / f"{asset['asset_id']}.jpg"
            download_file(asset["minio_path"], str(local_path))

            results = inference_model.predict(
                str(local_path),
                conf=conf,
                max_det=settings.bootstrap_max_detections,
                verbose=False,
            )
            local_path.unlink(missing_ok=True)

            for box in results[0].boxes:
                cls_index = int(box.cls[0])
                if cls_index not in index_to_id:
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                annotation_client.submit_suggestion(
                    asset_id=asset["asset_id"],
                    class_id=index_to_id[cls_index],
                    bbox_x=x1,
                    bbox_y=y1,
                    bbox_w=x2 - x1,
                    bbox_h=y2 - y1,
                    confidence=float(box.conf[0]),
                )
                suggestions_created += 1

        return {
            "status": "completed",
            "trained_on_images": len(list((extract_dir / "images").glob("*"))),
            "unlabeled_images_scanned": len(unlabeled),
            "suggestions_created": suggestions_created,
            "conf_threshold_used": conf,
        }
