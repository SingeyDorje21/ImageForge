import io
from PIL import Image

FORMAT_EXT_MAP = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}

def process_image(data: bytes, ext: str, operations: list[dict]) -> tuple[bytes, str]:
    """Apply operations sequentially via Pillow. Returns (result bytes, result extension)."""
    img = Image.open(io.BytesIO(data))
    result_ext = ext  # default to original extension

    for op in operations:
        op_type = op["type"]
        if op_type == "resize":
            img = img.resize((op["width"], op["height"]), Image.LANCZOS)
        elif op_type == "format_convert":
            target = op["target_format"]
            result_ext = f".{FORMAT_EXT_MAP.get(target, target)}"
            # Handle RGBA images for JPEG (no alpha channel support)
            if target in ("jpg", "jpeg") and img.mode == "RGBA":
                img = img.convert("RGB")

    # Determine save format from extension
    save_format = result_ext.lstrip(".").upper()
    if save_format == "JPG":
        save_format = "JPEG"

    out = io.BytesIO()
    img.save(out, format=save_format, quality=95)
    img.close()
    return out.getvalue(), result_ext
