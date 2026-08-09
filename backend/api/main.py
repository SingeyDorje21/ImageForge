import json
import os
import time
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Depends, File, Form, HTTPException, Query, UploadFile, status, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import aio_pika
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.staticfiles import StaticFiles

from api.schemas import (
    FormatConvertOperation,
    JobCreateResponse,
    JobStatusResponse,
    Operation,
    ResizeOperation,
)
from pydantic import BaseModel

class LoginRequest(BaseModel):
    password: str
from shared.database import get_db
from shared.models import Job
from api.config import get_settings

settings = get_settings()

STORAGE_PATH = settings.STORAGE_PATH
MAX_FILE_SIZE_MB = settings.MAX_FILE_SIZE_MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FORMAT_EXT_MAP = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(STORAGE_PATH, "originals"), exist_ok=True)
    os.makedirs(os.path.join(STORAGE_PATH, "results"), exist_ok=True)
    
    rabbitmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    rabbitmq_channel = await rabbitmq_connection.channel()
    
    await rabbitmq_channel.declare_queue(settings.DLQ_NAME, durable=True)
    await rabbitmq_channel.declare_queue(
        settings.RETRY_QUEUE_NAME, 
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": settings.QUEUE_NAME,
            "x-message-ttl": 5000,
        }
    )
    rabbitmq_queue = await rabbitmq_channel.declare_queue(settings.QUEUE_NAME, durable=True)
    
    app.state.rabbitmq_channel = rabbitmq_channel
    app.state.rabbitmq_queue = rabbitmq_queue
    app.state.rabbitmq_connection = rabbitmq_connection

    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client = redis.Redis(connection_pool=redis_pool)
    app.state.redis = redis_client
    
    yield
    
    await rabbitmq_connection.close()
    await redis_client.aclose()


app = FastAPI(
    title="ImageForge API",
    description="Asynchronous image processing service",
    version="0.1.4",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(STORAGE_PATH, exist_ok=True)
app.mount("/storage", StaticFiles(directory=STORAGE_PATH), name="storage")


async def verify_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    current_minute = int(time.time() / 60)
    redis_key = f"rate_limit:{client_ip}:{current_minute}"
    redis_client = request.app.state.redis
    
    count = await redis_client.incr(redis_key)
    
    if count == 1:
        await redis_client.expire(redis_key, 60)
        
    if count > 10:
        await redis_client.incr("metrics:rate_limit:hits")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 uploads per minute.",
        )


def _validate_file_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def _parse_operations(operations_json: str) -> list[dict]:
    try:
        ops_raw = json.loads(operations_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid operations JSON: {e}",
        )
    if not isinstance(ops_raw, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Operations must be a JSON array",
        )

    validated: list[dict] = []
    for i, op in enumerate(ops_raw):
        op_type = op.get("type")
        try:
            if op_type == "resize":
                parsed = ResizeOperation(**op)
            elif op_type == "format_convert":
                parsed = FormatConvertOperation(**op)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown operation type '{op_type}' at index {i}",
                )
            validated.append(parsed.model_dump())
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid operation at index {i}: {exc}",
            )
    return validated


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_rate_limit)])
async def create_job(
    file: UploadFile = File(...),
    operations: str = Form(...),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    filename = file.filename or "unknown.jpg"
    safe_filename = os.path.basename(filename)
    ext = _validate_file_extension(safe_filename)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit",
        )

    ops_validated = _parse_operations(operations)
    original_dir = f"{STORAGE_PATH}/originals"
    
    job = Job(
        original_filename=safe_filename,
        original_path="",
        operations=ops_validated,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_id_str = str(job.id)
    original_path = f"{original_dir}/{job_id_str}{ext}"

    try:
        with open(original_path, "wb") as f:
            f.write(content)

        job.original_path = original_path
        await db.commit()
        await db.refresh(job)

        channel = request.app.state.rabbitmq_channel
        message_body = json.dumps({"job_id": job_id_str}).encode()
        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(
            message,
            routing_key=settings.QUEUE_NAME,
        )
        
        # Metrics: Queued
        await request.app.state.redis.incr("metrics:jobs:queued")

    except Exception as e:
        job.original_path = original_path
        job.status = "failed"
        job.error_message = str(e)
        await db.commit()
        await db.refresh(job)

    return JobCreateResponse(job_id=job.id, status=job.status)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    redis_client = request.app.state.redis
    cache_key = f"job:{job_id}"
    
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            return JobStatusResponse.model_validate_json(cached_data)
        except Exception:
            pass
            
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
        
    response = JobStatusResponse(
        job_id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        result_path=job.result_path,
        operations=job.operations,
        retry_count=job.retry_count,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    
    if job.status in ("completed", "failed"):
        await redis_client.setex(cache_key, 3600, response.model_dump_json())
        
    return response


@app.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        query = query.where(Job.status == status_filter)
    query = query.limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()
    return [
        JobStatusResponse(
            job_id=j.id,
            status=j.status,
            original_filename=j.original_filename,
            result_path=j.result_path,
            operations=j.operations,
            retry_count=j.retry_count,
            error_message=j.error_message,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]


@app.get("/metrics")
async def get_metrics(request: Request):
    """Retrieve global system metrics from Redis."""
    redis_client = request.app.state.redis
    
    queued = await redis_client.get("metrics:jobs:queued") or 0
    completed = await redis_client.get("metrics:jobs:completed") or 0
    failed = await redis_client.get("metrics:jobs:failed") or 0
    rate_limits = await redis_client.get("metrics:rate_limit:hits") or 0
    total_time = await redis_client.get("metrics:jobs:total_time_sec") or 0.0
    
    completed_int = int(completed)
    avg_time = round(float(total_time) / completed_int, 3) if completed_int > 0 else 0.0
    
    return {
        "jobs_queued": int(queued),
        "jobs_completed": completed_int,
        "jobs_failed": int(failed),
        "rate_limit_hits": int(rate_limits),
        "avg_processing_time_sec": avg_time
    }


@app.post("/login")
async def login(req: LoginRequest):
    if req.password == settings.ADMIN_PASSWORD:
        return {"token": "admin-token-xyz"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
