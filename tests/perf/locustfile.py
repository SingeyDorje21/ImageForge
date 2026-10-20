"""
ImageForge load test (Locust).

Each simulated user uploads an image with a chain of operations, polls the job
until it finishes, then downloads the result through its signed URL. Besides the
per-request stats Locust always reports, every job is recorded as one extra
"JOB" entry whose response time is upload -> completed, so the report shows
job throughput and end-to-end p50/p95 next to the HTTP numbers.

It never calls /login or any admin endpoint.

Settings (environment variables):
    IMAGE_SIZE      source image, WIDTHxHEIGHT          (default 1920x1080)
    OPS_PROFILE     light | chain | heavy                (default chain)
    PACING_SECONDS  min seconds between uploads per user (default 15; 0 = no pause)
    POLL_SECONDS    seconds between status polls         (default 1)
    JOB_TIMEOUT     seconds before a job counts as stuck (default 120)
    DOWNLOAD        download the result, true/false      (default true)

See tests/perf/README.md for how to run it locally and against Cloud Run.
"""
import io
import json
import os
import random
import time

from locust import HttpUser, constant, constant_pacing, events, task
from PIL import Image

IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1920x1080")
OPS_PROFILE = os.getenv("OPS_PROFILE", "chain")
PACING_SECONDS = float(os.getenv("PACING_SECONDS", "15"))
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "1"))
JOB_TIMEOUT = float(os.getenv("JOB_TIMEOUT", "120"))
DOWNLOAD = os.getenv("DOWNLOAD", "true").lower() in ("1", "true", "yes")
RATE_LIMIT_BACKOFF = 10  # seconds a user pauses after a 429

OPS_PROFILES = {
    # Cheapest useful job: shrink and re-encode
    "light": [
        {"type": "resize", "width": 640, "height": 360},
        {"type": "format_convert", "target_format": "webp"},
    ],
    # What the UI typically sends: a few chained edits
    "chain": [
        {"type": "resize", "width": 1280, "height": 720},
        {"type": "rotate", "degrees": 90, "expand": True},
        {"type": "sharpen", "radius": 2, "percent": 150},
        {"type": "watermark", "text": "ImageForge", "position": "bottom_right", "opacity": 0.5, "font_size": 32},
        {"type": "quality", "quality": 85},
        {"type": "format_convert", "target_format": "jpg"},
    ],
    # Full-resolution filters, the slowest operations per pixel
    "heavy": [
        {"type": "blur", "radius": 8},
        {"type": "sharpen", "radius": 4, "percent": 200},
        {"type": "grayscale"},
        {"type": "watermark", "text": "ImageForge", "position": "center", "opacity": 0.4, "font_size": 96},
        {"type": "format_convert", "target_format": "png"},
    ],
}

if OPS_PROFILE not in OPS_PROFILES:
    raise SystemExit(f"OPS_PROFILE must be one of {', '.join(OPS_PROFILES)}")
OPERATIONS = json.dumps(OPS_PROFILES[OPS_PROFILE])


def _make_image() -> bytes:
    """A noisy JPEG, so it compresses like a photo rather than a flat colour."""
    width, height = (int(v) for v in IMAGE_SIZE.lower().split("x"))
    img = Image.effect_noise((width, height), 64).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


IMAGE_BYTES = _make_image()


@events.test_start.add_listener
def _describe(environment, **_):
    print(
        f"ImageForge load test: image {IMAGE_SIZE} ({len(IMAGE_BYTES) // 1024} KB), "
        f"ops={OPS_PROFILE}, pacing={PACING_SECONDS}s, download={DOWNLOAD}"
    )


class ImageJobUser(HttpUser):
    wait_time = constant_pacing(PACING_SECONDS) if PACING_SECONDS > 0 else constant(0)

    def _record_job(self, start: float, exc: Exception | None = None):
        events.request.fire(
            request_type="JOB",
            name=f"upload -> completed ({OPS_PROFILE})",
            response_time=(time.perf_counter() - start) * 1000,
            response_length=0,
            exception=exc,
            context={},
        )

    @task
    def process_image(self):
        start = time.perf_counter()
        filename = f"perf-{random.randint(0, 1_000_000)}.jpg"
        with self.client.post(
            "/jobs",
            files={"file": (filename, IMAGE_BYTES, "image/jpeg")},
            data={"operations": OPERATIONS},
            name="POST /jobs",
            catch_response=True,
        ) as resp:
            if resp.status_code != 202:
                # 429 here means the per-IP upload limit was hit; slow down or raise it
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")
                self._record_job(start, Exception(f"upload HTTP {resp.status_code}"))
                if resp.status_code == 429:
                    time.sleep(RATE_LIMIT_BACKOFF)  # don't keep hammering a limit that resets per minute
                return
            job_id = resp.json()["job_id"]

        job = None
        while time.perf_counter() - start < JOB_TIMEOUT:
            time.sleep(POLL_SECONDS)
            with self.client.get(f"/jobs/{job_id}", name="GET /jobs/[id]", catch_response=True) as resp:
                if resp.status_code != 200:
                    resp.failure(f"HTTP {resp.status_code}")
                    continue
                data = resp.json()
            if data["status"] in ("completed", "failed"):
                job = data
                break

        if job is None:
            self._record_job(start, Exception(f"not finished after {JOB_TIMEOUT:.0f}s"))
            return
        if job["status"] == "failed":
            self._record_job(start, Exception(f"job failed: {job.get('error_message')}"))
            return
        self._record_job(start)

        if DOWNLOAD and job.get("result_url"):
            # Signed URL on the storage host, not the API; Locust accepts absolute URLs
            with self.client.get(job["result_url"], name="GET result (signed URL)", catch_response=True) as resp:
                if resp.status_code != 200 or not resp.content:
                    resp.failure(f"HTTP {resp.status_code}")
