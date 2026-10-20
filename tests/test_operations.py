"""Unit tests for the image operations. No services needed: run with `pytest tests/test_operations.py`."""
import os
import sys

import pytest
from PIL import Image
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from api.schemas import OPERATION_MODELS  # noqa: E402
from worker.processor import InvalidOperationError, process_image  # noqa: E402


def _validated(ops):
    return [OPERATION_MODELS[op["type"]](**op).model_dump() for op in ops]


@pytest.fixture
def make_image(tmp_path):
    def _make(mode="RGB", size=(100, 50), color="red", fmt="PNG", ext=".png", exif=None):
        img = Image.new(mode, size, color)
        path = tmp_path / f"original{ext}"
        kwargs = {"exif": exif} if exif is not None else {}
        img.save(path, format=fmt, **kwargs)
        return str(path), ext
    return _make


@pytest.fixture
def run(tmp_path):
    out_dir = tmp_path / "results"
    out_dir.mkdir()

    def _run(original, ops):
        path, ext = original
        result = process_image(path, str(out_dir), "job", ext, _validated(ops))
        return result, Image.open(result)
    return _run


def test_crop(make_image, run):
    _, img = run(make_image(), [{"type": "crop", "left": 10, "top": 5, "width": 40, "height": 20}])
    assert img.size == (40, 20)


def test_crop_out_of_bounds_is_unrecoverable(make_image, run):
    with pytest.raises(InvalidOperationError):
        run(make_image(), [{"type": "crop", "left": 90, "top": 0, "width": 20, "height": 20}])


def test_rotate_expands_canvas(make_image, run):
    _, img = run(make_image(), [{"type": "rotate", "degrees": 90}])
    assert img.size == (50, 100)


def test_rotate_without_expand_keeps_size(make_image, run):
    _, img = run(make_image(), [{"type": "rotate", "degrees": 45, "expand": False}])
    assert img.size == (100, 50)


def test_flip_horizontal_and_vertical(tmp_path, run):
    src = Image.new("RGB", (2, 2), "black")
    src.putpixel((0, 0), (255, 0, 0))
    path = tmp_path / "corner.png"
    src.save(path)

    _, h = run((str(path), ".png"), [{"type": "flip", "direction": "horizontal"}])
    assert h.getpixel((1, 0)) == (255, 0, 0)
    _, v = run((str(path), ".png"), [{"type": "flip", "direction": "vertical"}])
    assert v.getpixel((0, 1)) == (255, 0, 0)


def test_quality_shrinks_jpeg(tmp_path, run):
    # A noisy image so compression level actually matters
    src = Image.effect_noise((200, 200), 64).convert("RGB")
    path = tmp_path / "noise.jpg"
    src.save(path, quality=95)

    high, _ = run((str(path), ".jpg"), [{"type": "quality", "quality": 95}])
    high_size = os.path.getsize(high)
    low, _ = run((str(path), ".jpg"), [{"type": "quality", "quality": 10}])
    assert os.path.getsize(low) < high_size


def test_exif_kept_by_default_and_stripped_on_request(make_image, run):
    exif = Image.Exif()
    exif[0x010F] = "TestCamera"  # Make
    original = make_image(fmt="JPEG", ext=".jpg", exif=exif.tobytes())

    _, kept = run(original, [{"type": "resize", "width": 50, "height": 25}])
    assert kept.getexif().get(0x010F) == "TestCamera"

    _, stripped = run(original, [{"type": "strip_exif"}])
    assert 0x010F not in stripped.getexif()


def test_watermark_changes_the_corner_only(make_image, run):
    _, img = run(make_image(size=(200, 100), color="blue"),
                 [{"type": "watermark", "text": "IF", "position": "bottom_right", "opacity": 1, "font_size": 30}])
    assert img.mode == "RGB"
    assert img.getpixel((5, 5)) == (0, 0, 255)
    corner = img.crop((150, 60, 200, 100))
    red_min, red_max = corner.getextrema()[0]
    assert red_max > 0


def test_watermark_keeps_alpha(make_image, run):
    _, img = run(make_image(mode="RGBA", color=(0, 0, 0, 0)), [{"type": "watermark", "text": "x"}])
    assert img.mode == "RGBA"


def test_grayscale(make_image, run):
    _, img = run(make_image(), [{"type": "grayscale"}])
    assert img.mode == "L"


def test_grayscale_rgba_to_jpeg(make_image, run):
    _, img = run(make_image(mode="RGBA"), [{"type": "grayscale"}, {"type": "format_convert", "target_format": "jpg"}])
    assert img.format == "JPEG"
    assert img.mode == "L"


def test_blur_softens_an_edge(tmp_path, run):
    src = Image.new("RGB", (40, 40), "black")
    src.paste((255, 255, 255), (20, 0, 40, 40))
    path = tmp_path / "edge.png"
    src.save(path)

    _, img = run((str(path), ".png"), [{"type": "blur", "radius": 4}])
    r, _, _ = img.getpixel((19, 20))
    assert 0 < r < 255


def test_sharpen_runs_on_palette_image(tmp_path, run):
    path = tmp_path / "palette.png"
    Image.new("RGB", (30, 30), "green").convert("P").save(path)
    _, img = run((str(path), ".png"), [{"type": "sharpen"}])
    assert img.size == (30, 30)


def test_chained_operations(make_image, run):
    result, img = run(make_image(size=(400, 300)), [
        {"type": "crop", "left": 0, "top": 0, "width": 300, "height": 300},
        {"type": "resize", "width": 100, "height": 100},
        {"type": "rotate", "degrees": 180},
        {"type": "grayscale"},
        {"type": "watermark", "text": "ImageForge"},
        {"type": "quality", "quality": 70},
        {"type": "format_convert", "target_format": "webp"},
    ])
    assert result.endswith(".webp")
    assert img.size == (100, 100)


@pytest.mark.parametrize("op", [
    {"type": "crop", "left": -1, "top": 0, "width": 10, "height": 10},
    {"type": "crop", "left": 0, "top": 0, "width": 0, "height": 10},
    {"type": "rotate", "degrees": 720},
    {"type": "flip", "direction": "diagonal"},
    {"type": "quality", "quality": 0},
    {"type": "quality", "quality": 101},
    {"type": "watermark", "text": ""},
    {"type": "watermark", "text": "x", "opacity": 1.5},
    {"type": "watermark", "text": "x", "position": "middle"},
    {"type": "blur", "radius": 0},
    {"type": "sharpen", "percent": 1000},
])
def test_schema_rejects_bad_params(op):
    with pytest.raises(ValidationError):
        OPERATION_MODELS[op["type"]](**op)
