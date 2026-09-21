import fnmatch
import subprocess
import tempfile
import uuid
from pathlib import Path

from celery import Celery
from PIL import Image

from .config import settings
from .db import SessionLocal
from .models import Dataset, DatasetAsset
from .storage import upload_file
from .windows_path import resolve_windows_path

# Users import their own industrial/AOI captures here (e.g. large
# uncompressed BMPs from line-scan cameras), not arbitrary internet
# content — Pillow's decompression-bomb guard (default ~179 megapixels)
# is meant for untrusted input and just rejects legitimate large frames.
Image.MAX_IMAGE_PIXELS = None

celery_app = Celery("dataset", broker=settings.celery_broker_url, backend=settings.celery_broker_url)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff"}

# Single-channel high-bit-depth modes (16/32-bit height maps, line-scan
# captures, etc.) — common for industrial/AOI TIFFs. A plain .convert("RGB")
# divides by a fixed factor and clips detail since real values rarely span
# the full 16/32-bit range; stretch each image's own min–max to 0–255 first
# so the actual content (e.g. a wire bond) stays visible and high-contrast.
HIGH_BITDEPTH_MODES = {"I", "I;16", "I;16B", "I;16L", "I;16N", "F"}


def _open_normalized_rgb(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode in HIGH_BITDEPTH_MODES:
        lo, hi = im.getextrema()
        scale = 255.0 / (hi - lo) if hi > lo else 0.0
        im = im.point(lambda v: (v - lo) * scale).convert("L")
    return im.convert("RGB")


def _resolve_source_path(source_path: str) -> Path:
    return resolve_windows_path(source_path, settings.mounted_drive_set)


def _store_asset(db, dataset_id: uuid.UUID, local_jpg_path: Path, frame_index: int | None) -> None:
    with Image.open(local_jpg_path) as im:
        width, height = im.size
        thumb = im.copy()
        thumb.thumbnail((settings.dataset_thumb_size, settings.dataset_thumb_size))
        thumb_path = local_jpg_path.with_name(f"thumb_{local_jpg_path.name}")
        thumb.convert("RGB").save(thumb_path, "JPEG", quality=85)

    object_name = f"{dataset_id}/raw/{local_jpg_path.name}"
    thumb_object_name = f"{dataset_id}/thumbs/{local_jpg_path.name}"
    upload_file(object_name, str(local_jpg_path), content_type="image/jpeg")
    upload_file(thumb_object_name, str(thumb_path), content_type="image/jpeg")

    db.add(
        DatasetAsset(
            dataset_id=dataset_id,
            minio_path=object_name,
            width=width,
            height=height,
            frame_index=frame_index,
        )
    )


def _process_video(db, dataset: Dataset, work_dir: Path) -> tuple[int, int]:
    interval = settings.dataset_frame_interval_sec
    pattern = str(work_dir / "frame_%08d.jpg")
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(_resolve_source_path(dataset.source_path)),
            "-vf", f"fps=1/{interval}",
            "-qscale:v", "2",
            pattern,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")

    frames = sorted(work_dir.glob("frame_*.jpg"))
    successes = failures = 0
    for idx, frame_path in enumerate(frames):
        try:
            _store_asset(db, dataset.dataset_id, frame_path, frame_index=idx)
            successes += 1
        except Exception:
            failures += 1
    return successes, failures


def _process_image_folder(db, dataset: Dataset, work_dir: Path) -> tuple[int, int]:
    source_dir = _resolve_source_path(dataset.source_path)
    files = sorted(p for p in source_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
    if dataset.filename_pattern:
        files = [p for p in files if fnmatch.fnmatch(p.name, dataset.filename_pattern)]
    successes = failures = 0
    for path in files:
        try:
            normalized = work_dir / f"{uuid.uuid4().hex}.jpg"
            with _open_normalized_rgb(path) as im:
                im.save(normalized, "JPEG", quality=95)
            _store_asset(db, dataset.dataset_id, normalized, frame_index=None)
            successes += 1
        except Exception:
            # One bad file (corrupt, unsupported variant, etc.) shouldn't
            # sink the whole batch — skip it and keep going.
            failures += 1
    return successes, failures


@celery_app.task(name="dataset.ingest")
def ingest_dataset(dataset_id: str) -> dict:
    db = SessionLocal()
    try:
        dataset = db.get(Dataset, uuid.UUID(dataset_id))
        if dataset is None:
            return {"dataset_id": dataset_id, "status": "not_found"}

        dataset.status = "processing"
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            if dataset.source_type == "video":
                successes, failures = _process_video(db, dataset, work_dir)
            else:
                successes, failures = _process_image_folder(db, dataset, work_dir)

        if successes == 0:
            dataset.status = "failed"
            db.commit()
            return {"dataset_id": dataset_id, "status": "failed", "error": "no files could be processed"}

        dataset.status = "ready"
        db.commit()
        return {"dataset_id": dataset_id, "status": "ready", "assets": successes, "skipped": failures}
    except Exception as exc:
        db.rollback()
        dataset = db.get(Dataset, uuid.UUID(dataset_id))
        if dataset is not None:
            dataset.status = "failed"
            db.commit()
        return {"dataset_id": dataset_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
