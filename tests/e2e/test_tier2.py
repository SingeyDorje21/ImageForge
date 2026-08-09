import pytest
import json
import uuid

# --- Feature 1: POST /jobs (Submission) ---

def test_f1_empty_operations_list(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f1_missing_file(api_client):
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", data=data)
    assert resp.status_code == 422

def test_f1_missing_operations(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    resp = api_client.post("/jobs", files=files)
    assert resp.status_code == 422

def test_f1_extra_fields_in_form_data(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {
        "operations": json.dumps([{"type": "resize", "width": 100, "height": 100}]),
        "extra_field": "some_value"
    }
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_f1_huge_operations_list(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    ops = [{"type": "resize", "width": 100, "height": 100} for _ in range(50)]
    data = {"operations": json.dumps(ops)}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202


# --- Feature 2: POST /jobs (File Validation) ---

def test_f2_0_byte_file(api_client):
    files = {"file": ("image.png", b"", "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f2_exactly_10mb_file(api_client):
    # Simulating a 10MB file
    img = b"0" * (10 * 1024 * 1024)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_f2_over_10mb_file(api_client):
    img = b"0" * ((10 * 1024 * 1024) + 1)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 413

def test_f2_1x1_pixel_image(api_client, image_factory):
    img = image_factory(width=1, height=1)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202

def test_f2_mismatched_extension_vs_content(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.txt", img, "text/plain")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422


# --- Feature 3: POST /jobs (Schema Validation) ---

def test_f3_unknown_operation_type(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "rotate", "degrees": 90}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f3_missing_required_fields(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100}])} # missing height
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f3_zero_dimensions(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 0, "height": 0}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f3_negative_dimensions(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": -100, "height": -100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f3_type_mismatch_in_values(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": "one hundred", "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422


# --- Feature 4: GET /jobs/{job_id} ---

def test_f4_invalid_uuid_format(api_client):
    resp = api_client.get("/jobs/12345-abcde")
    assert resp.status_code == 422

def test_f4_non_existent_uuid(api_client):
    resp = api_client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404

def test_f4_uppercase_uuid(api_client):
    job_id = str(uuid.uuid4()).upper()
    resp = api_client.get(f"/jobs/{job_id}")
    assert resp.status_code == 404

def test_f4_trailing_slash(api_client):
    job_id = str(uuid.uuid4())
    resp = api_client.get(f"/jobs/{job_id}/", allow_redirects=False)
    assert resp.status_code == 404

def test_f4_sql_injection_string(api_client):
    resp = api_client.get("/jobs/' OR 1=1--")
    assert resp.status_code == 422


# --- Feature 5: GET /jobs (Listing/Filters) ---

def test_f5_limit_0(api_client):
    resp = api_client.get("/jobs?limit=0")
    assert resp.status_code == 422

def test_f5_limit_100(api_client):
    resp = api_client.get("/jobs?limit=100")
    assert resp.status_code == 200

def test_f5_limit_101(api_client):
    resp = api_client.get("/jobs?limit=101")
    assert resp.status_code == 422

def test_f5_negative_limit(api_client):
    resp = api_client.get("/jobs?limit=-5")
    assert resp.status_code == 422

def test_f5_unknown_status_filter(api_client):
    resp = api_client.get("/jobs?status=UNKNOWN_STATUS")
    assert resp.status_code == 422


# --- Feature 6: Image Resize ---

def _submit_and_wait(api_client, wait_for_job, files, data):
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    return wait_for_job(job_id)

def test_f6_extreme_downscale(api_client, image_factory, wait_for_job):
    img = image_factory(width=2000, height=2000)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 1, "height": 1}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f6_extreme_upscale(api_client, image_factory, wait_for_job):
    img = image_factory(width=1, height=1)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 2000, "height": 2000}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f6_extreme_aspect_ratio_change(api_client, image_factory, wait_for_job):
    img = image_factory(width=100, height=100)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 1000, "height": 1}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f6_float_dimensions(api_client, image_factory):
    img = image_factory()
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100.5, "height": 100.5}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f6_same_dimensions(api_client, image_factory, wait_for_job):
    img = image_factory(width=100, height=100)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"


# --- Feature 7: Image Format Convert ---

def test_f7_convert_to_same_format(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "format_convert", "target_format": "png"}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f7_uppercase_target_format(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "format_convert", "target_format": "WEBP"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f7_convert_transparent_png_to_jpeg(api_client, image_factory, wait_for_job):
    from PIL import Image
    import io
    # Create transparent PNG
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="png")
    files = {"file": ("image.png", buf.getvalue(), "image/png")}
    data = {"operations": json.dumps([{"type": "format_convert", "target_format": "jpg"}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f7_unsupported_target_format(api_client, image_factory):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "format_convert", "target_format": "gif"}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422

def test_f7_lossy_to_lossless(api_client, image_factory, wait_for_job):
    img = image_factory(format="jpeg")
    files = {"file": ("image.jpg", img, "image/jpeg")}
    data = {"operations": json.dumps([{"type": "format_convert", "target_format": "png"}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"


# --- Feature 8: Chained Operations ---

def test_f8_conflicting_format_converts(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    ops = [
        {"type": "format_convert", "target_format": "webp"},
        {"type": "format_convert", "target_format": "jpg"}
    ]
    data = {"operations": json.dumps(ops)}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f8_redundant_resizes(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    ops = [
        {"type": "resize", "width": 500, "height": 500},
        {"type": "resize", "width": 100, "height": 100}
    ]
    data = {"operations": json.dumps(ops)}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f8_convert_then_resize(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    ops = [
        {"type": "format_convert", "target_format": "webp"},
        {"type": "resize", "width": 50, "height": 50}
    ]
    data = {"operations": json.dumps(ops)}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f8_many_operations(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    ops = [{"type": "resize", "width": 100 + i, "height": 100 + i} for i in range(10)]
    data = {"operations": json.dumps(ops)}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"

def test_f8_alternating_formats(api_client, image_factory, wait_for_job):
    img = image_factory(format="png")
    files = {"file": ("image.png", img, "image/png")}
    ops = [
        {"type": "format_convert", "target_format": "jpg"},
        {"type": "format_convert", "target_format": "webp"},
        {"type": "format_convert", "target_format": "png"}
    ]
    data = {"operations": json.dumps(ops)}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "completed"


# --- Feature 9: Processing Error Handling ---

def test_f9_valid_headers_corrupted_data(api_client, image_factory, wait_for_job):
    # Valid PNG signature, corrupted data
    corrupt_img = b"\x89PNG\r\n\x1a\n" + b"garbage" * 100
    files = {"file": ("image.png", corrupt_img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "failed"

def test_f9_text_file_renamed_to_jpg(api_client, wait_for_job):
    text_data = b"This is just some text content."
    files = {"file": ("image.jpg", text_data, "image/jpeg")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "failed"

def test_f9_pdf_renamed_to_png(api_client, wait_for_job):
    pdf_data = b"%PDF-1.4\n1 0 obj\n<< /Title (Dummy) >>\nendobj\n"
    files = {"file": ("image.png", pdf_data, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "failed"

def test_f9_decompression_bomb(api_client, image_factory, wait_for_job):
    # Simulating a very small file but we will just pass corrupt=True to image_factory
    # Since we can't easily generate a real decompression bomb here, we'll use corrupt
    img = image_factory(corrupt=True)
    files = {"file": ("image.png", img, "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    res = _submit_and_wait(api_client, wait_for_job, files, data)
    assert res["status"] == "failed"

def test_f9_empty_array_file_payload(api_client):
    files = {"file": ("image.png", b"", "image/png")}
    data = {"operations": json.dumps([{"type": "resize", "width": 100, "height": 100}])}
    resp = api_client.post("/jobs", files=files, data=data)
    assert resp.status_code == 422


# --- Feature 10: Health Check ---

def test_f10_post_to_health(api_client):
    resp = api_client.post("/health")
    assert resp.status_code == 405

def test_f10_query_parameters(api_client):
    resp = api_client.get("/health?verbose=true")
    assert resp.status_code == 200

def test_f10_trailing_slash(api_client):
    resp = api_client.get("/health/", allow_redirects=False)
    assert resp.status_code == 404

def test_f10_headers_variations(api_client):
    resp = api_client.get("/health", headers={"Accept": "application/xml"})
    assert resp.status_code == 200

def test_f10_body_on_get(api_client):
    resp = api_client.get("/health", json={"data": "test"})
    # Some frameworks ignore the body, some return 400/422
    assert resp.status_code == 200
