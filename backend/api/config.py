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
    QUEUE_BACKEND: str = "rabbitmq"  # "rabbitmq" or "cloudtasks"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_NAME: str = "image_jobs"
    RETRY_QUEUE_NAME: str = "image_jobs_retry"
    DLQ_NAME: str = "image_jobs_dlq"
    MAX_RETRIES: int = 3
    # Cloud Tasks (QUEUE_BACKEND=cloudtasks)
    GCP_PROJECT: str | None = None
    GCP_LOCATION: str = "us-central1"
    CLOUD_TASKS_QUEUE: str = "image-jobs"
    WORKER_URL: str = "http://localhost:8080"  # base URL of the worker.server service
    TASKS_SERVICE_ACCOUNT: str | None = None  # signs OIDC tokens for the private worker
    REDIS_URL: str = "redis://localhost:6379/0"
    # No default: admin login stays disabled until ADMIN_PASSWORD is set.
    ADMIN_PASSWORD: str | None = None
    # Key used to sign admin tokens. Set a long random value in production.
    JWT_SECRET: str | None = None
    TOKEN_TTL_MINUTES: int = 60
    # Failed admin logins allowed per client IP within the window before /login returns 429.
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 900
    # Set to true behind a proxy that appends the client IP to X-Forwarded-For
    # (e.g. Google Cloud Run), so rate limits count each user separately.
    TRUST_PROXY_HEADERS: bool = False
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
