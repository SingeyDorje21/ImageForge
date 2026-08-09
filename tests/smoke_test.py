"""
ImageForge Phase 2 -- Smoke Test Script (Async version)
Programmatically exercises all acceptance criteria.
Requires: API running on localhost:8000, Postgres running and migrated.

Usage:
    python tests/smoke_test.py
"""

import io
import json
import sys
import time
import requests
from PIL import Image

BASE_URL = "http://localhost:8000"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} -- {detail}")
        failed += 1


def create_test_image(width=640, height=480, color="red", fmt="PNG") -> tuple[io.BytesIO, str]:
    """Create a test image in memory and return (buffer, extension)."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    ext_map = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
    return buf, ext_map.get(fmt, ".png")

def wait_for_job(job_id: str, timeout: int = 15) -> dict:
    """Poll the job status until it is no longer pending or processing."""
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if r.status_code == 200:
            data = r.json()
            if data.get("status") not in ("pending", "processing"):
                return data
        time.sleep(1)
    return {}


def main():
    print("=" * 60)
    print("ImageForge Phase 2 -- Smoke Test")
    print("=" * 60)

    # --- 1. Health Check ---
    print("\n[1] Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        check("GET /health returns 200", r.status_code == 200)
        check("GET /health body", r.json().get("status") == "ok", f"got {r.json()}")
    except Exception as e:
        check("GET /health reachable", False, str(e))
        print("\n[!] API is not running. Start it with: uvicorn api.main:app --reload")
        sys.exit(1)

    # --- 2. Resize Operation ---
    print("\n[2] Resize Operation")
    buf, ext = create_test_image(640, 480, "blue", "PNG")
    ops = json.dumps([{"type": "resize", "width": 400, "height": 300}])
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": (f"test_resize{ext}", buf, "image/png")},
        data={"operations": ops},
    )
    check("POST /jobs (resize) returns 202", r.status_code == 202, f"got {r.status_code}")
    body = r.json()
    check("Response has job_id", "job_id" in body, f"body: {body}")
    check("Initial status is pending", body.get("status") == "pending", f"got {body.get('status')}")
    resize_job_id = body.get("job_id")

    # Verify dimensions via GET after polling
    if resize_job_id:
        job_data = wait_for_job(resize_job_id)
        check("Job eventually completed", job_data.get("status") == "completed", f"got {job_data.get('status')}")
        check("Job has result_path", job_data.get("result_path") is not None, f"got {job_data}")

        # Open the result file and check dimensions
        result_path = job_data.get("result_path")
        if result_path:
            try:
                img = Image.open(result_path)
                check("Result image is 400x300", img.size == (400, 300), f"got {img.size}")
                img.close()
            except Exception as e:
                check("Result image readable", False, str(e))

    # --- 3. Format Conversion (PNG -> WebP) ---
    print("\n[3] Format Conversion (PNG -> WebP)")
    buf, ext = create_test_image(320, 240, "green", "PNG")
    ops = json.dumps([{"type": "format_convert", "target_format": "webp"}])
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": (f"test_convert{ext}", buf, "image/png")},
        data={"operations": ops},
    )
    check("POST /jobs (format_convert) returns 202", r.status_code == 202)
    body = r.json()
    convert_job_id = body.get("job_id")
    check("Initial status is pending", body.get("status") == "pending")

    if convert_job_id:
        job_data = wait_for_job(convert_job_id)
        check("Status is completed", job_data.get("status") == "completed")
        result_path = job_data.get("result_path")
        if result_path:
            check("Result file ends with .webp", result_path.endswith(".webp"), f"got {result_path}")
            try:
                img = Image.open(result_path)
                check("Result is valid WebP", img.format == "WEBP", f"got {img.format}")
                img.close()
            except Exception as e:
                check("Result WebP readable", False, str(e))

    # --- 4. Format Conversion (JPG -> PNG) ---
    print("\n[4] Format Conversion (JPG -> PNG)")
    buf, ext = create_test_image(200, 200, "yellow", "JPEG")
    ops = json.dumps([{"type": "format_convert", "target_format": "png"}])
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": ("test_jpg2png.jpg", buf, "image/jpeg")},
        data={"operations": ops},
    )
    check("POST /jobs (jpg->png) returns 202", r.status_code == 202)
    body = r.json()
    if body.get("job_id"):
        job_data = wait_for_job(body["job_id"])
        result_path = job_data.get("result_path")
        if result_path:
            try:
                img = Image.open(result_path)
                check("Result is valid PNG", img.format == "PNG", f"got {img.format}")
                img.close()
            except Exception as e:
                check("Result PNG readable", False, str(e))

    # --- 5. Chained Operations ---
    print("\n[5] Chained Operations (resize + format_convert)")
    buf, ext = create_test_image(800, 600, "purple", "PNG")
    ops = json.dumps([
        {"type": "resize", "width": 200, "height": 200},
        {"type": "format_convert", "target_format": "webp"},
    ])
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": (f"test_chain{ext}", buf, "image/png")},
        data={"operations": ops},
    )
    check("POST /jobs (chained) returns 202", r.status_code == 202)
    body = r.json()
    if body.get("job_id"):
        job_data = wait_for_job(body["job_id"])
        result_path = job_data.get("result_path")
        if result_path:
            try:
                img = Image.open(result_path)
                check("Chained: 200x200", img.size == (200, 200), f"got {img.size}")
                check("Chained: WebP format", img.format == "WEBP", f"got {img.format}")
                img.close()
            except Exception as e:
                check("Chained result readable", False, str(e))

    # --- 6. Job Status Tracking ---
    print("\n[6] Job Status Tracking")
    if resize_job_id:
        r = requests.get(f"{BASE_URL}/jobs/{resize_job_id}")
        check("GET /jobs/{id} returns 200", r.status_code == 200)
        data = r.json()
        check("Has created_at", "created_at" in data)
        check("Has updated_at", "updated_at" in data)
        check("Has result_path", "result_path" in data)
        check("Has retry_count", "retry_count" in data)

    # Non-existent job
    r = requests.get(f"{BASE_URL}/jobs/00000000-0000-0000-0000-000000000000")
    check("GET non-existent job returns 404", r.status_code == 404)

    # List jobs with status filter
    r = requests.get(f"{BASE_URL}/jobs", params={"status": "completed"})
    check("GET /jobs?status=completed returns 200", r.status_code == 200)
    jobs_list = r.json()
    check("All returned jobs are completed",
          all(j["status"] == "completed" for j in jobs_list),
          f"got statuses: {[j['status'] for j in jobs_list]}")

    # List jobs with limit
    r = requests.get(f"{BASE_URL}/jobs", params={"limit": 5})
    check("GET /jobs?limit=5 returns <= 5 jobs", len(r.json()) <= 5, f"got {len(r.json())}")

    # --- 7. Error Handling ---
    print("\n[7] Error Handling")

    # Non-image file
    buf = io.BytesIO(b"this is not an image")
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": ("test.txt", buf, "text/plain")},
        data={"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])},
    )
    check("Non-image file returns 400", r.status_code == 400, f"got {r.status_code}")

    # Invalid operations JSON
    buf, ext = create_test_image(100, 100, "red", "PNG")
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": (f"test{ext}", buf, "image/png")},
        data={"operations": "not valid json {{{"},
    )
    check("Invalid JSON returns 422", r.status_code == 422, f"got {r.status_code}")

    # Invalid operation type
    buf, ext = create_test_image(100, 100, "red", "PNG")
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": (f"test{ext}", buf, "image/png")},
        data={"operations": json.dumps([{"type": "blur", "radius": 5}])},
    )
    check("Unknown operation type returns 422", r.status_code == 422, f"got {r.status_code}")

    # --- Summary ---
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print("All tests passed!")
    else:
        print("Some tests failed -- see details above.")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
