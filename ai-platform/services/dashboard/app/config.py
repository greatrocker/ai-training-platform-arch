from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_host: str = "redis"
    redis_port: int = 6379

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
