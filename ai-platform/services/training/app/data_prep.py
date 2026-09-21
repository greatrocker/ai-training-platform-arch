"""Shared helper for pulling a dataset's current annotations out of
annotation-service as YOLO-format training data. Used by both the
throwaway bootstrap-label flow and real training_job runs.
"""

import zipfile
from pathlib import Path

from . import annotation_client
from .storage import download_file


def class_index_map(dataset_id: str) -> tuple[dict[int, int], dict[int, int], list[str]]:
    schema = annotation_client.get_schema(dataset_id)
    classes = sorted(schema["classes"], key=lambda c: c["class_id"])
    if not classes:
        raise ValueError("no label classes defined for this dataset yet")
    id_to_index = {c["class_id"]: i for i, c in enumerate(classes)}
    index_to_id = {i: c["class_id"] for i, c in enumerate(classes)}
    names = [c["class_name"] for c in classes]
    return id_to_index, index_to_id, names


def has_any_label(labels_dir: Path) -> bool:
    for txt in labels_dir.glob("*.txt"):
        if txt.read_text().strip():
            return True
    return False


def download_and_extract(dataset_id: str, export_format: str, tmp_path: Path) -> Path:
    """export_format: 'yolo' (bbox) or 'yolo-seg' (polygon/mask). Returns
    the directory containing images/, labels/, classes.txt."""
    export = annotation_client.export_yolo(dataset_id, export_format)
    zip_path = tmp_path / "export.zip"
    download_file(export["object_name"], str(zip_path))

    extract_dir = tmp_path / "data"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    return extract_dir
