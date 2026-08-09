"""
Test failure handling and resilience (Phase 3).
"""

import io
import json
import time
import requests
import sys

BASE_URL = "http://localhost:8000"

def check(name: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} -- {detail}")
        sys.exit(1)

def wait_for_job(job_id: str, timeout: int = 15) -> dict:
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
    print("ImageForge Phase 3 -- Resilience Test")
    print("=" * 60)

    # 1. Unrecoverable Error (Corrupt Image)
    print("\n[1] Unrecoverable Error (Corrupted Image File)")
    # Submit a text file disguised as a PNG
    buf = io.BytesIO(b"This is definitely not a valid PNG image file data.")
    ops = json.dumps([{"type": "resize", "width": 100, "height": 100}])
    r = requests.post(
        f"{BASE_URL}/jobs",
        files={"file": ("fake_image.png", buf, "image/png")},
        data={"operations": ops},
    )
    check("POST returns 202", r.status_code == 202)
    job_id = r.json()["job_id"]
    
    # It should fail quickly without retrying
    job_data = wait_for_job(job_id, timeout=10)
    check("Status is failed", job_data.get("status") == "failed", f"Got status: {job_data.get('status')}")
    check("Retry count is 0", job_data.get("retry_count") == 0, f"Got retry_count: {job_data.get('retry_count')}")
    check("Has error message", "Unrecoverable" in job_data.get("error_message", ""), f"Msg: {job_data.get('error_message')}")

    print("\n============================================================")
    print("Resilience tests passed!")

if __name__ == "__main__":
    main()
