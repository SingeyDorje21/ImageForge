from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    DATABASE_URL: str = "postgresql+asyncpg://imageforge:imageforge@localhost:5433/imageforge"
    STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE_MB: int = 10
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_NAME: str = "image_jobs"
    RETRY_QUEUE_NAME: str = "image_jobs_retry"
    DLQ_NAME: str = "image_jobs_dlq"
    MAX_RETRIES: int = 3
    REDIS_URL: str = "redis://localhost:6379/0"
    # No default: admin login stays disabled until ADMIN_PASSWORD is set.
    ADMIN_PASSWORD: str | None = None
    # Key used to sign admin tokens. Set a long random value in production.
    JWT_SECRET: str | None = None
    TOKEN_TTL_MINUTES: int = 60
    # Comma-separated list of origins allowed to call the API from a browser.
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
