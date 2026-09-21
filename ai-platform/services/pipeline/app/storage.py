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

_public_client = Minio(
    settings.minio_public_endpoint,
    access_key=settings.minio_root_user,
    secret_key=settings.minio_root_password,
    secure=settings.minio_use_ssl,
    region="us-east-1",
)


def _ensure_bucket() -> None:
    if not _client.bucket_exists(settings.minio_bucket_cctv):
        _client.make_bucket(settings.minio_bucket_cctv)


def upload_snapshot(object_name: str, file_path: str) -> str:
    _ensure_bucket()
    _client.fput_object(settings.minio_bucket_cctv, object_name, file_path, content_type="image/jpeg")
    return object_name


def presigned_snapshot_url(object_name: str) -> str:
    return _public_client.presigned_get_object(
        settings.minio_bucket_cctv, object_name, expires=timedelta(hours=1)
    )
