from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResizeOperation(BaseModel):
    type: Literal["resize"]
    width: int = Field(gt=0, le=10000)
    height: int = Field(gt=0, le=10000)


class FormatConvertOperation(BaseModel):
    type: Literal["format_convert"]
    target_format: Literal["jpg", "png", "webp"]


# Union type for operations
Operation = ResizeOperation | FormatConvertOperation


class JobCreateResponse(BaseModel):
    """Response schema for POST /jobs."""
    job_id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    """Response schema for GET /jobs/{job_id}."""
    job_id: UUID
    status: str
    original_filename: str
    result_path: str | None = None
    operations: list[dict]
    retry_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Response schema for GET /jobs list."""
    jobs: list[JobStatusResponse]
    count: int
