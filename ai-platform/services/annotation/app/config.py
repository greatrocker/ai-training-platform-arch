from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mssql_host: str = "mssql"
    mssql_port: int = 1433
    mssql_sa_password: str = "changeme"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_database: str = "ai_annotation"

    annotation_ai_confidence_threshold: float = 0.6
    annotation_risk_score_threshold: float = 0.5
    annotation_vlm_model: str = "qwen2.5-vl-7b"
    annotation_vlm_endpoint: str = ""  # OpenAI-vision-compatible chat/completions URL; empty = not configured
    annotation_auto_approve: bool = False

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_dataset: str = "datasets"

    redis_host: str = "redis"
    redis_port: int = 6379

    dataset_service_url: str = "http://dataset-service:8000"

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}@{self.mssql_host}:{self.mssql_port}"
            f"/{self.mssql_database}?driver={driver}&TrustServerCertificate=yes"
        )

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/2"


settings = Settings()
