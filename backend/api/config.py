from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    DATABASE_URL: str = "postgresql+asyncpg://imageforge:imageforge@localhost:5433/imageforge"
    S3_BUCKET: str = "imageforge"
    S3_ENDPOINT_URL: str | None = None  # unset = AWS S3; set for R2, MinIO, GCS, Spaces
    S3_PUBLIC_ENDPOINT_URL: str | None = None  # host used in signed URLs, if different
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_FORCE_PATH_STYLE: bool = False
    S3_URL_EXPIRY_SECONDS: int = 3600
    S3_CREATE_BUCKET: bool = False  # create the bucket on API startup (local dev)
    MAX_FILE_SIZE_MB: int = 10
    RATE_LIMIT_PER_MINUTE: int = 10  # uploads per client IP
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_NAME: str = "image_jobs"
    RETRY_QUEUE_NAME: str = "image_jobs_retry"
    DLQ_NAME: str = "image_jobs_dlq"
    MAX_RETRIES: int = 3
    REDIS_URL: str = "redis://localhost:6379/0"
    ADMIN_PASSWORD: str = "imageforge_admin_123"
    CORS_ORIGINS: str = "*"  # comma-separated list of allowed origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
