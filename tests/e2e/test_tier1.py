import pytest
import json
import uuid

# Feature 1: POST /jobs (Submission)
def test_submit_valid_png(api_client, image_factory):
    file_bytes = image_factory("png")
    files = {"file": ("test.png", file_bytes, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_submit_valid_jpg(api_client, image_factory):
    file_bytes = image_factory("jpeg")
    files = {"file": ("test.jpg", file_bytes, "image/jpeg")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_submit_valid_webp(api_client, image_factory):
    file_bytes = image_factory("webp")
    files = {"file": ("test.webp", file_bytes, "image/webp")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_submit_response_structure(api_client, image_factory):
    file_bytes = image_factory("png")
    files = {"file": ("test.png", file_bytes, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202
    resp_json = resp.json()
    assert "job_id" in resp_json
    assert "status" in resp_json

def test_submit_creates_job_in_list(api_client, image_factory):
    file_bytes = image_factory("png")
    files = {"file": ("test.png", file_bytes, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_id = resp.json()["job_id"]
    
    list_resp = api_client.get("/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert any(j.get("job_id") == job_id for j in jobs)

# Feature 2: POST /jobs (File Validation)
def test_submit_empty_file(api_client):
    files = {"file": ("empty.png", b"", "image/png")}
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code in [400, 422]

def test_submit_non_image_extension(api_client):
    files = {"file": ("test.txt", b"hello text", "text/plain")}
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code in [400, 422]

def test_submit_missing_file(api_client):
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", data=data)
    assert resp.status_code == 422

def test_submit_oversized_file(api_client):
    files = {"file": ("big.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")}
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 413

def test_submit_invalid_mime_type(api_client, image_factory):
    file_bytes = image_factory("jpeg")
    files = {"file": ("test.jpg", file_bytes, "application/json")}
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code in [400, 422]

# Feature 3: POST /jobs (Schema Validation)
def test_submit_invalid_json_operations(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": "not json"}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_submit_missing_operations(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    resp = api_client.post("/jobs", files=files)
    assert resp.status_code == 422

def test_submit_operations_not_list(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps({"type": "resize"})}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_submit_missing_required_op_field(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_submit_unknown_operation(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "rotate", "angle": 90}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

# Feature 4: GET /jobs/{job_id}
def test_get_job_exists(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_id = resp.json()["job_id"]
    
    get_resp = api_client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200

def test_get_job_structure(api_client, image_factory):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_id = resp.json()["job_id"]
    
    get_resp = api_client.get(f"/jobs/{job_id}")
    j = get_resp.json()
    assert "status" in j
    assert "retry_count" in j
    assert "created_at" in j
    assert "updated_at" in j

def test_get_job_not_found(api_client):
    fake_id = str(uuid.uuid4())
    resp = api_client.get(f"/jobs/{fake_id}")
    assert resp.status_code == 404

def test_get_job_invalid_uuid(api_client):
    resp = api_client.get("/jobs/not-a-uuid")
    assert resp.status_code == 422

def test_get_job_result_path(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 10, "height": 10}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_id = resp.json()["job_id"]
    
    job_data = wait_for_job(job_id)
    assert job_data["status"] == "completed"
    assert "result_path" in job_data

# Feature 5: GET /jobs (Listing/Filters)
def test_list_jobs_success(api_client):
    resp = api_client.get("/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_list_jobs_default_limit(api_client):
    resp = api_client.get("/jobs")
    assert len(resp.json()) <= 20

def test_list_jobs_custom_limit(api_client):
    resp = api_client.get("/jobs?limit=5")
    assert len(resp.json()) <= 5

def test_list_jobs_filter_completed(api_client):
    resp = api_client.get("/jobs?status=completed")
    for j in resp.json():
        assert j["status"] == "completed"

def test_list_jobs_filter_pending(api_client):
    resp = api_client.get("/jobs?status=pending")
    for j in resp.json():
        assert j["status"] == "pending"

# Feature 6: Image Resize
def test_resize_standard(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 400, "height": 300}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_id = resp.json()["job_id"]
    
    job_data = wait_for_job(job_id)
    assert job_data["status"] == "completed"
    
    res_url = job_data["result_path"]
    img_resp = api_client.get(res_url)
    assert img_resp.status_code == 200
    
def test_resize_downscale(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", width=1000, height=1000), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 50, "height": 50}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_resize_upscale(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", width=10, height=10), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 1000, "height": 1000}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_resize_maintains_format(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 10, "height": 10}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_resize_result_accessible(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 10, "height": 10}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"
    assert api_client.get(job_data["result_path"]).status_code == 200

# Feature 7: Image Format Convert
def test_convert_png_to_jpg(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "convert", "target_format": "jpg"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_convert_jpg_to_webp(api_client, image_factory, wait_for_job):
    files = {"file": ("test.jpg", image_factory("jpeg"), "image/jpeg")}
    data = {"operations": json.dumps([{"type": "convert", "target_format": "webp"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_convert_webp_to_png(api_client, image_factory, wait_for_job):
    files = {"file": ("test.webp", image_factory("webp"), "image/webp")}
    data = {"operations": json.dumps([{"type": "convert", "target_format": "png"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_convert_same_format(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "convert", "target_format": "png"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_convert_quality(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([{"type": "convert", "target_format": "jpg"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

# Feature 8: Chained Operations
def test_chain_resize_then_convert(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([
        {"type": "resize", "width": 50, "height": 50},
        {"type": "convert", "target_format": "jpg"}
    ])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_chain_convert_then_resize(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([
        {"type": "convert", "target_format": "jpg"},
        {"type": "resize", "width": 50, "height": 50}
    ])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_chain_multiple_resizes(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([
        {"type": "resize", "width": 100, "height": 100},
        {"type": "resize", "width": 50, "height": 50}
    ])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_chain_multiple_converts(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([
        {"type": "convert", "target_format": "jpg"},
        {"type": "convert", "target_format": "webp"}
    ])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

def test_chain_valid_job_completion(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png"), "image/png")}
    data = {"operations": json.dumps([
        {"type": "resize", "width": 100, "height": 100},
        {"type": "convert", "target_format": "jpg"},
        {"type": "resize", "width": 50, "height": 50}
    ])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "completed"

# Feature 9: Processing Error Handling
def test_processing_corrupt_image(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", corrupt=True), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "failed"

def test_processing_failure_message(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", corrupt=True), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "failed"
    assert job_data.get("error_message") is not None

def test_processing_failure_result_path(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", corrupt=True), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "failed"
    assert not job_data.get("result_path")

def test_processing_failure_retry_count(api_client, image_factory, wait_for_job):
    files = {"file": ("test.png", image_factory("png", corrupt=True), "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    job_data = wait_for_job(resp.json()["job_id"])
    assert job_data["status"] == "failed"
    assert "retry_count" in job_data

def test_processing_unsupported_image(api_client, image_factory, wait_for_job):
    files = {"file": ("test.tiff", image_factory("tiff"), "image/tiff")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    if resp.status_code == 202:
        job_data = wait_for_job(resp.json()["job_id"])
        assert job_data["status"] == "failed"
    else:
        assert resp.status_code in [400, 422]

# Feature 10: Health Check & CORS
def test_health_check_status(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200

def test_health_check_response(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert "status" in resp.json()

def test_cors_headers_present(api_client):
    resp = api_client.options("/jobs")
    assert resp.status_code in [200, 204]

def test_invalid_endpoint(api_client):
    resp = api_client.get("/nonexistent")
    assert resp.status_code == 404

def test_invalid_method(api_client):
    resp = api_client.put("/jobs")
    assert resp.status_code == 405
