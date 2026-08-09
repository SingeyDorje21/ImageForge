import pytest
import io
import json
from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from shared.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Attempt to setup DB for testing if necessary
    import asyncio
    asyncio.run(init_db())

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "ImageForge API is running"}

def create_dummy_image(ext="png"):
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format=ext)
    buf.seek(0)
    return buf.read()

def test_file_upload():
    img_data = create_dummy_image()
    files = {'file': ('test.png', img_data, 'image/png')}
    response = client.post("/jobs", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "completed"
    assert "id" in data

def test_file_upload_invalid_extension():
    files = {'file': ('test.txt', b'hello world', 'text/plain')}
    response = client.post("/jobs", files=files)
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]

def test_file_upload_large():
    # Need > 10MB
    large_data = b"0" * (11 * 1024 * 1024)
    files = {'file': ('large.png', large_data, 'image/png')}
    response = client.post("/jobs", files=files)
    assert response.status_code == 400
    assert "exceeds 10MB limit" in response.json()["detail"]

def test_image_processing_resize():
    img_data = create_dummy_image()
    operations = json.dumps([{"type": "resize", "width": 50, "height": 50}])
    files = {'file': ('test_resize.png', img_data, 'image/png')}
    response = client.post("/jobs", files=files, data={"operations": operations})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "completed"

def test_get_jobs():
    response = client.get("/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_job():
    img_data = create_dummy_image()
    files = {'file': ('test.png', img_data, 'image/png')}
    post_res = client.post("/jobs", files=files)
    job_id = post_res.json()["id"]

    get_res = client.get(f"/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id
