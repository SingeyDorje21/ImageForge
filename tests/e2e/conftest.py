import os
import io
import time
import pytest
import requests
from PIL import Image

@pytest.fixture
def api_client():
    base_url = os.environ.get("API_URL", "http://localhost:8000")
    session = requests.Session()
    
    class APIClient:
        def __init__(self, session, base_url):
            self.session = session
            self.base_url = base_url

        def request(self, method, path, **kwargs):
            url = f"{self.base_url}{path}"
            return self.session.request(method, url, **kwargs)
            
        def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
        def post(self, path, **kwargs): return self.request("POST", path, **kwargs)
        def options(self, path, **kwargs): return self.request("OPTIONS", path, **kwargs)
        def put(self, path, **kwargs): return self.request("PUT", path, **kwargs)
        def patch(self, path, **kwargs): return self.request("PATCH", path, **kwargs)
        def delete(self, path, **kwargs): return self.request("DELETE", path, **kwargs)

    yield APIClient(session, base_url)

@pytest.fixture
def image_factory():
    def _create_image(format="png", width=100, height=100, color="red", corrupt=False):
        if corrupt:
            return b"this is not a valid image format but has extension " + format.encode()
        
        img = Image.new("RGB", (width, height), color=color)
        buf = io.BytesIO()
        img.save(buf, format=format)
        return buf.getvalue()
        
    return _create_image

@pytest.fixture
def wait_for_job(api_client):
    def _wait(job_id, timeout=10, interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            resp = api_client.get(f"/jobs/{job_id}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") in ["completed", "failed"]:
                    return data
            time.sleep(interval)
        raise TimeoutError(f"Job {job_id} did not finish within {timeout} seconds")
    return _wait
