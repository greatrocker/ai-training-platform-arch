from datetime import timedelta

from minio import Minio

from .config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_root_user,
    secret_key=settings.minio_root_password,
    secure=settings.minio_use_ssl,
    region="us-east-1",
)

# Pinned region so presigning never needs a live connection to
# minio_public_endpoint just to look up the bucket's region — see the note
# in dataset-service/app/storage.py for the full story.
_public_client = Minio(
    settings.minio_public_endpoint,
    access_key=settings.minio_root_user,
    secret_key=settings.minio_root_password,
    secure=settings.minio_use_ssl,
    region="us-east-1",
)


def upload_file(object_name: str, file_path: str, content_type: str = "application/octet-stream") -> str:
    _client.fput_object(settings.minio_bucket_dataset, object_name, file_path, content_type=content_type)
    return object_name


def download_file(object_name: str, dest_path: str) -> None:
    _client.fget_object(settings.minio_bucket_dataset, object_name, dest_path)


def presigned_download_url(object_name: str) -> str:
    return _public_client.presigned_get_object(
        settings.minio_bucket_dataset, object_name, expires=timedelta(hours=1)
    )
