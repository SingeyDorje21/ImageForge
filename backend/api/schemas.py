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


class CropOperation(BaseModel):
    """Crop a box whose top-left corner is (left, top)."""
    type: Literal["crop"]
    left: int = Field(ge=0, le=10000)
    top: int = Field(ge=0, le=10000)
    width: int = Field(gt=0, le=10000)
    height: int = Field(gt=0, le=10000)


class RotateOperation(BaseModel):
    """Rotate counter-clockwise by `degrees`. `expand` grows the canvas to fit."""
    type: Literal["rotate"]
    degrees: float = Field(ge=-360, le=360)
    expand: bool = True


class FlipOperation(BaseModel):
    type: Literal["flip"]
    direction: Literal["horizontal", "vertical"]


class QualityOperation(BaseModel):
    """Output quality for lossy formats (JPEG, WebP). PNG output is optimized instead."""
    type: Literal["quality"]
    quality: int = Field(ge=1, le=100)


class StripExifOperation(BaseModel):
    """Drop EXIF metadata (camera, GPS, timestamps) from the output."""
    type: Literal["strip_exif"]


class WatermarkOperation(BaseModel):
    type: Literal["watermark"]
    text: str = Field(min_length=1, max_length=200)
    position: Literal["top_left", "top_right", "bottom_left", "bottom_right", "center"] = "bottom_right"
    opacity: float = Field(default=0.5, ge=0, le=1)
    font_size: int = Field(default=24, ge=8, le=500)


class GrayscaleOperation(BaseModel):
    type: Literal["grayscale"]


class BlurOperation(BaseModel):
    type: Literal["blur"]
    radius: float = Field(default=2, gt=0, le=100)


class SharpenOperation(BaseModel):
    """Unsharp mask: `percent` is strength, `radius` the blur size it sharpens against."""
    type: Literal["sharpen"]
    radius: float = Field(default=2, gt=0, le=100)
    percent: int = Field(default=150, ge=1, le=500)


# Union type for operations
Operation = (
    ResizeOperation
    | FormatConvertOperation
    | CropOperation
    | RotateOperation
    | FlipOperation
    | QualityOperation
    | StripExifOperation
    | WatermarkOperation
    | GrayscaleOperation
    | BlurOperation
    | SharpenOperation
)

# Maps each operation's `type` to the schema that validates it
OPERATION_MODELS: dict[str, type[BaseModel]] = {
    "resize": ResizeOperation,
    "format_convert": FormatConvertOperation,
    "crop": CropOperation,
    "rotate": RotateOperation,
    "flip": FlipOperation,
    "quality": QualityOperation,
    "strip_exif": StripExifOperation,
    "watermark": WatermarkOperation,
    "grayscale": GrayscaleOperation,
    "blur": BlurOperation,
    "sharpen": SharpenOperation,
}


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
