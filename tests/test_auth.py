"""
Security regression tests for admin auth and CORS. Runs in-process, no services needed.

Usage:
    pytest tests/test_auth.py
"""
import os
import sys
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.update(
    ADMIN_PASSWORD="test-password",
    JWT_SECRET="test-secret-" + "x" * 32,
    CORS_ORIGINS="http://localhost:5173,https://app.example.com",
)

from api import auth  # noqa: E402
from api.main import app  # noqa: E402


class FakeRedis:
    async def get(self, key):
        return None


@asynccontextmanager
async def fake_lifespan(app):
    app.state.redis = FakeRedis()
    yield


app.router.lifespan_context = fake_lifespan


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client):
    resp = client.post("/login", json={"password": "test-password"})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_wrong_password_rejected(client):
    assert client.post("/login", json={"password": "nope"}).status_code == 401


def test_old_default_password_rejected(client):
    assert client.post("/login", json={"password": "imageforge_admin_123"}).status_code == 401


@pytest.mark.parametrize("path", ["/metrics", "/jobs"])
def test_admin_endpoints_require_token(client, path):
    assert client.get(path).status_code == 401


def test_old_fixed_token_rejected(client):
    resp = client.get("/metrics", headers={"Authorization": "Bearer admin-token-xyz"})
    assert resp.status_code == 401


def test_valid_token_accepted(client, token):
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_tampered_token_rejected(client, token):
    header, payload, signature = token.split(".")
    forged = auth._b64encode(b'{"sub":"admin","iat":0,"exp":9999999999}')
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {header}.{forged}.{signature}"})
    assert resp.status_code == 401


def test_expired_token_rejected(client, token, monkeypatch):
    real_time = auth.time.time
    monkeypatch.setattr(auth.time, "time", lambda: real_time() + 2 * 3600)
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_login_disabled_without_password(client, monkeypatch):
    monkeypatch.setattr(auth.get_settings(), "ADMIN_PASSWORD", None)
    assert client.post("/login", json={"password": ""}).status_code == 503


def test_cors_allows_configured_origin(client):
    resp = client.options(
        "/metrics",
        headers={"Origin": "https://app.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == "https://app.example.com"


def test_cors_blocks_other_origin(client):
    resp = client.options(
        "/metrics",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in resp.headers
