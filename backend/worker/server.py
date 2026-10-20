"""HTTP worker for push queues (Google Cloud Tasks).

Cloud Tasks POSTs {"job_id": ...} to /tasks/process and retries the task with
backoff whenever the response is not 2xx. Run with:

    uvicorn worker.server:app --host 0.0.0.0 --port 8080

On Cloud Run, deploy this service without public access; Cloud Tasks
authenticates with an OIDC token for a service account that has the invoker
role, so only the queue can reach it.
"""
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response, status
from pydantic import BaseModel

from api.config import get_settings
from worker.jobs import Outcome, run_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskPayload(BaseModel):
    job_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis.Redis(connection_pool=redis_pool)
    yield
    await app.state.redis.aclose()


app = FastAPI(title="ImageForge Worker", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/tasks/process")
async def process_task(payload: TaskPayload, request: Request):
    outcome = await run_job(payload.job_id, request.app.state.redis)
    if outcome == Outcome.RETRY:
        # Non-2xx makes Cloud Tasks redeliver after its backoff
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    # Everything else is final; acknowledge so the task is not retried
    return {"job_id": payload.job_id, "outcome": outcome.value}
