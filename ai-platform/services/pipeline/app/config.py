from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mssql_host: str = "mssql"
    mssql_port: int = 1433
    mssql_sa_password: str = "changeme"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_database: str = "ai_pipeline"

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_cctv: str = "cctv-snapshots"

    # Fernet key (32 url-safe base64 bytes) used to encrypt cctv_device
    # RTSP passwords at rest. Generate with:
    #   openssl rand -base64 32 | tr '+/' '-_'
    pipeline_encryption_key: str = "changeme-32-byte-fernet-key-000000000000="

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}@{self.mssql_host}:{self.mssql_port}"
            f"/{self.mssql_database}?driver={driver}&TrustServerCertificate=yes"
        )


settings = Settings()
