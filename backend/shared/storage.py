"""S3-compatible object storage (AWS S3, Cloudflare R2, GCS interop, MinIO, ...).

Objects are addressed by key, e.g. ``originals/<job_id>.png``. The key is what
gets stored on the Job row; browsers download through short-lived signed URLs.
"""
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from api.config import get_settings


def _make_client(endpoint_url: str | None):
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.S3_FORCE_PATH_STYLE else "auto"},
        ),
    )


@lru_cache
def _client():
    return _make_client(get_settings().S3_ENDPOINT_URL)


@lru_cache
def _signing_client():
    # Signed URLs embed the host, so they must be built against the endpoint
    # browsers can reach (e.g. localhost:9000 rather than minio:9000).
    settings = get_settings()
    return _make_client(settings.S3_PUBLIC_ENDPOINT_URL or settings.S3_ENDPOINT_URL)


def ensure_bucket() -> None:
    """Create the bucket if it does not exist yet."""
    bucket = get_settings().S3_BUCKET
    try:
        _client().head_bucket(Bucket=bucket)
    except ClientError:
        _client().create_bucket(Bucket=bucket)


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    extra = {"ContentType": content_type} if content_type else {}
    _client().put_object(Bucket=get_settings().S3_BUCKET, Key=key, Body=data, **extra)


def download_bytes(key: str) -> bytes:
    obj = _client().get_object(Bucket=get_settings().S3_BUCKET, Key=key)
    return obj["Body"].read()


def presigned_url(key: str, download_name: str | None = None) -> str:
    settings = get_settings()
    params = {"Bucket": settings.S3_BUCKET, "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
    return _signing_client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=settings.S3_URL_EXPIRY_SECONDS
    )
