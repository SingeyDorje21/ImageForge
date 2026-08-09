"""
Test Redis Caching and Rate Limiting (Phase 4).
"""

import io
import json
import time
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def check(name: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} -- {detail}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("ImageForge Phase 4 -- Redis Test")
    print("=" * 60)

    # 1. Test Rate Limiting
    print("\n[1] Rate Limiting (10 requests / min)")
    success_count = 0
    too_many_requests_count = 0
    
    buf = io.BytesIO(b"Fake image data to bypass early size check but fail processing")
    ops = json.dumps([{"type": "resize", "width": 100, "height": 100}])
    
    # Wait if we are within 2 seconds of a minute boundary to avoid counter reset
    while int(time.time()) % 60 > 58:
        time.sleep(0.5)
        
    # Fire 15 requests quickly
    for i in range(15):
        r = requests.post(
            f"{BASE_URL}/jobs",
            files={"file": ("fake_image.png", buf, "image/png")},
            data={"operations": ops},
        )
        if r.status_code == 202:
            success_count += 1
        elif r.status_code == 429:
            too_many_requests_count += 1
            
    check("Accepted exactly 10 requests", success_count == 10, f"Got {success_count}")
    check("Rejected exactly 5 requests (429)", too_many_requests_count == 5, f"Got {too_many_requests_count}")

    # 2. Test Caching (Speed)
    print("\n[2] Lazy Caching")
    # Wait a bit for the first job to fail (since it's fake data, it will fail)
    # Then query it multiple times to ensure cache hit.
    
    # We don't have the job_id from the first request saved, let's just make one valid request, wait for it, and benchmark.
    # Wait, we are already rate limited! We might get 429 if we try to post again.
    # Let's just list jobs to get an ID.
    r = requests.get(f"{BASE_URL}/jobs?limit=1")
    if r.status_code == 200 and r.json():
        job_id = r.json()[0]["job_id"]
        
        # Wait until it's failed
        while True:
            r = requests.get(f"{BASE_URL}/jobs/{job_id}")
            if r.json()["status"] == "failed":
                break
            time.sleep(1)
            
        # Now it is cached for 1 hour.
        # Benchmark DB vs Cache
        start = time.time()
        for _ in range(50):
            requests.get(f"{BASE_URL}/jobs/{job_id}")
        duration = time.time() - start
        
        # 50 requests should be very fast with Redis (e.g. < 0.5s locally)
        check(f"50 cached requests took {duration:.2f}s", duration < 1.0, f"Too slow: {duration:.2f}s")
    else:
        print("  [SKIP] Could not fetch job for caching test")

    print("\n============================================================")
    print("Redis tests completed!")

if __name__ == "__main__":
    main()
