from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mssql_host: str = "mssql"
    mssql_port: int = 1433
    mssql_sa_password: str = "changeme"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_database: str = "ai_monitor"

    redis_host: str = "redis"
    redis_port: int = 6379

    stream_protocol: str = "hls"
    alarm_sound_enabled: bool = True
    alarm_retention_days: int = 90

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        driver = self.mssql_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://sa:{self.mssql_sa_password}@{self.mssql_host}:{self.mssql_port}"
            f"/{self.mssql_database}?driver={driver}&TrustServerCertificate=yes"
        )


settings = Settings()
