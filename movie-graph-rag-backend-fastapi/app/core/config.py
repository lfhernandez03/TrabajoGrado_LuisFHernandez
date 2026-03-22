from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "movie-graph-rag-backend-fastapi"
    app_env: str = os.getenv("APP_ENV", "development")
    app_debug: bool = os.getenv("APP_ENV", "development") == "development"
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/movie-graph-rag")
    gemini_api_key: str = ""
    fuseki_url: str = os.getenv("FUSEKI_URL", "http://localhost:3030")
    fuseki_dataset: str = os.getenv("FUSEKI_DATASET", "movies")
    fuseki_user: str = os.getenv("FUSEKI_USER", "")
    fuseki_password: str = os.getenv("FUSEKI_PASSWORD", "")
    fuseki_timeout_seconds: int = int(os.getenv("FUSEKI_TIMEOUT_SECONDS", "8"))
    fuseki_max_retries: int = int(os.getenv("FUSEKI_MAX_RETRIES", "3"))
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    gemini_model: str = "gemini-2.5-flash"
    admin_emails: str = os.getenv("ADMIN_EMAILS", "")
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    def __init__(self, **data):
        super().__init__(**data)
        # Validaciones de seguridad al iniciar
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must be set in environment variables")
        if self.app_debug and self.app_env == "production":
            raise ValueError("app_debug cannot be True in production")
        if self.fuseki_user and not self.fuseki_password:
            raise ValueError("FUSEKI_PASSWORD must be provided if FUSEKI_USER is set")


settings = Settings()
