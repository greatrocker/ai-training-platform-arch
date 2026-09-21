from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mssql_host: str = "mssql"
    mssql_port: int = 1433
    mssql_sa_password: str = "changeme"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_database: str = "ai_training"

    redis_host: str = "redis"
    redis_port: int = 6379

    training_gpu_device: str = "0"
    training_max_concurrent_jobs: int = 2
    model_registry_default: str = "yolo11n"
    incremental_default_replay_ratio: float = 0.2
    incremental_default_lr: float = 0.001

    annotation_service_url: str = "http://annotation-service:8000"
    dataset_service_url: str = "http://dataset-service:8000"
    bootstrap_epochs: int = 100
    bootstrap_img_size: int = 320
    # With only a handful of training examples the model's confidence
    # calibration is poor even when box localization is already accurate
    # (observed in testing: a spatially-correct box at ~1% confidence) —
    # default errs low since every suggestion is human-reviewed before it
    # counts anyway. bootstrap_max_detections bounds the worst case so a
    # low threshold can't flood the review queue on a busy/noisy image.
    bootstrap_conf_threshold: float = 0.15
    # Kept small on purpose: tested with a real bootstrap run where the
    # single best (highest-confidence) box per image was consistently the
    # correct one, while lower-confidence extras were noise. Since the
    # review queue sorts by risk_score = 1-confidence descending, a large
    # max_detections buries the one good suggestion under noisy ones with
    # even lower confidence (higher risk) that surface first.
    bootstrap_max_detections: int = 3

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_dataset: str = "datasets"
    minio_bucket_models: str = "models"

    model_config = SettingsConfigDict(extra="ignore", protected_namespaces=())

    @property
    def sqlalchemy_url(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}@{self.mssql_host}:{self.mssql_port}"
            f"/{self.mssql_database}?driver={driver}&TrustServerCertificate=yes"
        )

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
