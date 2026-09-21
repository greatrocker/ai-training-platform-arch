from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    oauth2_issuer: str = "http://keycloak:8080/realms/ai-platform"
    oauth2_issuer_public: str = "http://localhost:8080/realms/ai-platform"
    oauth2_client_id: str = "ai-training-frontend"
    oauth2_client_secret: str = "changeme"
    oauth2_redirect_uri: str = "http://localhost/callback"
    jwt_algo: str = "RS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_min: int = 1440
    cookie_signing_secret: str = "changeme-dev-only"
    frontend_origin: str = "http://localhost"

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
