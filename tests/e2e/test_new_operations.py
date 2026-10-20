import json

import pytest

NEW_OPERATIONS = [
    {"type": "crop", "left": 10, "top": 10, "width": 50, "height": 50},
    {"type": "rotate", "degrees": 90},
    {"type": "flip", "direction": "horizontal"},
    {"type": "quality", "quality": 60},
    {"type": "strip_exif"},
    {"type": "watermark", "text": "ImageForge", "position": "center"},
    {"type": "grayscale"},
    {"type": "blur", "radius": 3},
    {"type": "sharpen"},
]


@pytest.mark.parametrize("op", NEW_OPERATIONS, ids=[op["type"] for op in NEW_OPERATIONS])
def test_new_operation_completes(api_client, image_factory, wait_for_job, op):
    files = {"file": ("test.jpg", image_factory("jpeg"), "image/jpeg")}
    resp = api_client.post("/jobs", files=files, data={"operations": json.dumps([op])})
    assert resp.status_code == 202
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"


def test_invalid_params_rejected(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "quality", "quality": 500}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422


def test_crop_outside_image_fails_without_retry(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", width=100, height=100), "image/png")}
    data = {"operations": json.dumps([{"type": "crop", "left": 80, "top": 0, "width": 50, "height": 50}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "failed"
    assert job_data["retry_count"] == 0
