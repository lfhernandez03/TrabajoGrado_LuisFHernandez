from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "movie-graph-rag-backend-fastapi"
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    mongo_uri: str = "mongodb://localhost:27017/movie-graph-rag"
    groq_api_key: str = ""
    fuseki_url: str = "http://localhost:3030"
    fuseki_dataset: str = "movies"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    groq_model: str = "llama-3.1-8b-instant"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
