import io
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FORMAT_EXT_MAP = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}

WATERMARK_MARGIN = 10


class InvalidOperationError(ValueError):
    """An operation can't be applied to this image (e.g. crop box outside it). Retrying won't help."""


def _ensure_filterable(img: Image.Image) -> Image.Image:
    """Palette and 1-bit images can't be filtered or drawn on with alpha; widen them first."""
    if img.mode in ("P", "1"):
        return img.convert("RGBA" if "transparency" in img.info else "RGB")
    return img


def _crop(img: Image.Image, op: dict) -> Image.Image:
    left, top, width, height = op["left"], op["top"], op["width"], op["height"]
    if left + width > img.width or top + height > img.height:
        raise InvalidOperationError(
            f"Crop box ({left}, {top}, {width}x{height}) exceeds image size {img.width}x{img.height}"
        )
    return img.crop((left, top, left + width, top + height))


def _watermark(img: Image.Image, op: dict) -> Image.Image:
    original_mode = img.mode
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default(size=op["font_size"])

    x0, y0, x1, y1 = draw.textbbox((0, 0), op["text"], font=font)
    text_w, text_h = x1 - x0, y1 - y0
    m = WATERMARK_MARGIN
    positions = {
        "top_left": (m, m),
        "top_right": (base.width - text_w - m, m),
        "bottom_left": (m, base.height - text_h - m),
        "bottom_right": (base.width - text_w - m, base.height - text_h - m),
        "center": ((base.width - text_w) // 2, (base.height - text_h) // 2),
    }
    x, y = positions[op["position"]]
    alpha = round(255 * op["opacity"])
    # Offset by the bbox origin so the visible glyphs, not the text origin, land at (x, y)
    draw.text((x - x0, y - y0), op["text"], font=font, fill=(255, 255, 255, alpha),
              stroke_width=max(1, op["font_size"] // 16), stroke_fill=(0, 0, 0, alpha))

    result = Image.alpha_composite(base, overlay)
    if original_mode in ("L", "LA"):
        return result.convert(original_mode)
    if "A" not in original_mode:
        return result.convert("RGB")
    return result


def _grayscale(img: Image.Image) -> Image.Image:
    has_alpha = "A" in img.mode or "transparency" in img.info
    return img.convert("LA" if has_alpha else "L")


def _prepare_for_save(img: Image.Image, save_format: str) -> Image.Image:
    """Convert to a mode the target format can store."""
    if save_format == "JPEG" and img.mode not in ("RGB", "L", "CMYK"):
        return img.convert("L" if img.mode == "LA" else "RGB")
    return img


def process_image(data: bytes, ext: str, operations: list[dict]) -> tuple[bytes, str]:
    """Apply operations sequentially via Pillow. Returns (result bytes, result extension)."""
    img = Image.open(io.BytesIO(data))
    result_ext = ext  # default to original extension
    exif = img.info.get("exif")  # carried through to the output unless stripped
    quality = 95

    for op in operations:
        op_type = op["type"]
        if op_type == "resize":
            img = img.resize((op["width"], op["height"]), Image.LANCZOS)
        elif op_type == "format_convert":
            target = op["target_format"]
            result_ext = f".{FORMAT_EXT_MAP.get(target, target)}"
        elif op_type == "crop":
            img = _crop(img, op)
        elif op_type == "rotate":
            img = _ensure_filterable(img).rotate(op["degrees"], resample=Image.BICUBIC, expand=op["expand"])
        elif op_type == "flip":
            img = ImageOps.mirror(img) if op["direction"] == "horizontal" else ImageOps.flip(img)
        elif op_type == "quality":
            quality = op["quality"]
        elif op_type == "strip_exif":
            exif = None
        elif op_type == "watermark":
            img = _watermark(_ensure_filterable(img), op)
        elif op_type == "grayscale":
            img = _grayscale(img)
        elif op_type == "blur":
            img = _ensure_filterable(img).filter(ImageFilter.GaussianBlur(op["radius"]))
        elif op_type == "sharpen":
            img = _ensure_filterable(img).filter(
                ImageFilter.UnsharpMask(radius=op["radius"], percent=op["percent"], threshold=3)
            )
        else:
            raise InvalidOperationError(f"Unknown operation type '{op_type}'")

    # Determine save format from extension
    save_format = result_ext.lstrip(".").upper()
    if save_format == "JPG":
        save_format = "JPEG"

    img = _prepare_for_save(img, save_format)
    save_kwargs = {"format": save_format}
    if save_format == "PNG":
        save_kwargs["optimize"] = True
    else:
        save_kwargs["quality"] = quality
    if exif:
        save_kwargs["exif"] = exif

    out = io.BytesIO()
    img.save(out, **save_kwargs)
    img.close()
    return out.getvalue(), result_ext
