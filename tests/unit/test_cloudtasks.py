"""Unit tests for the Cloud Tasks queue path (no GCP or infra needed).

Run from backend/:  python -m pytest ../tests/unit
"""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from shared.task_queue import CloudTasksQueue, create_queue
from worker import server
from worker.jobs import Outcome


class FakeClient:
    def __init__(self):
        self.tasks = []

    def queue_path(self, project, location, queue):
        return f"projects/{project}/locations/{location}/queues/{queue}"

    async def create_task(self, parent, task):
        self.tasks.append((parent, task))


def make_settings(**overrides):
    base = dict(
        QUEUE_BACKEND="cloudtasks",
        GCP_PROJECT="demo",
        GCP_LOCATION="europe-west1",
        CLOUD_TASKS_QUEUE="image-jobs",
        WORKER_URL="https://worker.example.run.app/",
        TASKS_SERVICE_ACCOUNT="tasks@demo.iam.gserviceaccount.com",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_publish_builds_authenticated_push_task():
    client = FakeClient()
    queue = CloudTasksQueue(make_settings(), client=client)
    asyncio.run(queue.publish("abc-123"))

    parent, task = client.tasks[0]
    assert parent == "projects/demo/locations/europe-west1/queues/image-jobs"
    req = task.http_request
    assert req.url == "https://worker.example.run.app/tasks/process"
    assert json.loads(req.body) == {"job_id": "abc-123"}
    assert req.oidc_token.service_account_email == "tasks@demo.iam.gserviceaccount.com"
    assert req.oidc_token.audience == "https://worker.example.run.app"


def test_publish_without_service_account_sends_no_token():
    client = FakeClient()
    queue = CloudTasksQueue(make_settings(TASKS_SERVICE_ACCOUNT=None), client=client)
    asyncio.run(queue.publish("abc-123"))
    assert not client.tasks[0][1].http_request.oidc_token.service_account_email


def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        asyncio.run(create_queue(make_settings(QUEUE_BACKEND="sqs")))


@pytest.mark.parametrize(
    "outcome,expected_status",
    [
        (Outcome.COMPLETED, 200),
        (Outcome.FAILED, 200),
        (Outcome.EXHAUSTED, 200),
        (Outcome.MISSING, 200),
        (Outcome.SKIPPED, 200),
        (Outcome.RETRY, 503),
    ],
)
def test_worker_only_asks_for_redelivery_on_transient_failure(monkeypatch, outcome, expected_status):
    async def fake_run_job(job_id, redis_client):
        return outcome

    monkeypatch.setattr(server, "run_job", fake_run_job)
    app = server.app
    app.router.lifespan_context = _no_lifespan
    with TestClient(app) as c:
        r = c.post("/tasks/process", json={"job_id": "abc-123"})
    assert r.status_code == expected_status


def test_worker_rejects_bad_payload():
    server.app.router.lifespan_context = _no_lifespan
    with TestClient(server.app) as c:
        assert c.post("/tasks/process", json={}).status_code == 422


from contextlib import asynccontextmanager


@asynccontextmanager
async def _no_lifespan(app):
    app.state.redis = None
    yield
