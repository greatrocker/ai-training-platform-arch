from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mssql_host: str = "mssql"
    mssql_port: int = 1433
    mssql_sa_password: str = "changeme"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_database: str = "ai_dataset"

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_dataset: str = "datasets"

    redis_host: str = "redis"
    redis_port: int = 6379

    dataset_frame_interval_sec: int = 1
    dataset_max_upload_gb: int = 50
    dataset_thumb_size: int = 320

    # Drive letters bind-mounted into this container at /mnt/host/<letter>
    # (see docker-compose.yml) — lets users type a normal Windows path
    # (e.g. D:\Videos\lineA) instead of a container-internal one.
    windows_drive_mounts: str = "c"

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def mounted_drive_set(self) -> set[str]:
        return {d.strip().lower() for d in self.windows_drive_mounts.split(",") if d.strip()}

    @property
    def sqlalchemy_url(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}@{self.mssql_host}:{self.mssql_port}"
            f"/{self.mssql_database}?driver={driver}&TrustServerCertificate=yes"
        )

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/1"


settings = Settings()
