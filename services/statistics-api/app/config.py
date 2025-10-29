"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - all values must come from environment variables."""

    # Application
    app_name: str = "statistics-api"
    app_version: str = "1.0.0"
    debug: bool = False

    # MongoDB - REQUIRED from environment
    mongodb_uri: str
    mongodb_database: str

    # Keycloak - REQUIRED from environment
    keycloak_server_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str = ""  # Optional, not used for public client

    # Device Registration API - REQUIRED from environment
    device_registration_api_url: str

    # CORS - comma-separated list of allowed origins
    cors_origins: str = "http://localhost:8080"

    # Valid device types (whitelist)
    valid_device_types: list[str] = ["ios", "android", "watch", "tv"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
