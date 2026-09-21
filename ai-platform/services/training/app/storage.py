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


def download_file(object_name: str, dest_path: str) -> None:
    _client.fget_object(settings.minio_bucket_dataset, object_name, dest_path)


def upload_model_weights(object_name: str, file_path: str) -> str:
    _client.fput_object(settings.minio_bucket_models, object_name, file_path, content_type="application/octet-stream")
    return object_name


def download_model_weights(object_name: str, dest_path: str) -> None:
    _client.fget_object(settings.minio_bucket_models, object_name, dest_path)


def presigned_model_url(object_name: str) -> str:
    return _public_client.presigned_get_object(
        settings.minio_bucket_models, object_name, expires=timedelta(hours=1)
    )
