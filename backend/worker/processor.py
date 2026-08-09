import os
from PIL import Image

FORMAT_EXT_MAP = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}

def process_image(original_path: str, result_dir: str, job_id: str, ext: str, operations: list[dict]) -> str:
    """Apply operations sequentially via Pillow. Returns the result file path."""
    img = Image.open(original_path)
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

    result_path = os.path.join(result_dir, f"{job_id}{result_ext}")

    # Determine save format from extension
    save_format = result_ext.lstrip(".").upper()
    if save_format == "JPG":
        save_format = "JPEG"

    img.save(result_path, format=save_format, quality=95)
    img.close()
    return result_path
