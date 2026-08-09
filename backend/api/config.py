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
    ADMIN_PASSWORD: str = "imageforge_admin_123"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
