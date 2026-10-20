"""Job processing shared by the RabbitMQ consumer and the HTTP (Cloud Tasks) worker."""
import asyncio
import logging
import os
import time
from enum import Enum

import redis.asyncio as redis
from PIL import UnidentifiedImageError
from sqlalchemy import select

from api.config import get_settings
from shared import storage
from shared.database import async_session_maker
from shared.models import Job
from worker.processor import InvalidOperationError, process_image

logger = logging.getLogger(__name__)

CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


class Outcome(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"        # unrecoverable, e.g. not an image
    RETRY = "retry"          # transient failure, should be redelivered
    EXHAUSTED = "exhausted"  # transient failure, out of retries
    MISSING = "missing"      # no such job
    SKIPPED = "skipped"      # already finished (duplicate delivery)


async def run_job(job_id: str, redis_client: redis.Redis) -> Outcome:
    settings = get_settings()
    logger.info(f"Processing job {job_id}")
    start_time = time.time()

    async with async_session_maker() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalars().first()
        if not job:
            logger.error(f"Job {job_id} not found in DB")
            return Outcome.MISSING

        # Deliveries are at-least-once; don't redo finished work
        if job.status in ("completed", "failed"):
            logger.info(f"Job {job_id} already {job.status}, skipping")
            return Outcome.SKIPPED

        job.status = "processing"
        await session.commit()
        await session.refresh(job)

        original_path = job.original_path
        ext = os.path.splitext(original_path)[1]

        try:
            original = await asyncio.to_thread(storage.download_bytes, original_path)
            result_bytes, result_ext = await asyncio.to_thread(
                process_image,
                data=original,
                ext=ext,
                operations=job.operations,
            )
            result_path = f"results/{job.id}{result_ext}"
            await asyncio.to_thread(
                storage.upload_bytes, result_path, result_bytes, CONTENT_TYPES.get(result_ext)
            )

            job.result_path = result_path
            job.status = "completed"
            await session.commit()
            logger.info(f"Job {job_id} completed successfully")

            # Metrics: Success
            await redis_client.incr("metrics:jobs:completed")
            duration = time.time() - start_time
            await redis_client.incrbyfloat("metrics:jobs:total_time_sec", duration)
            return Outcome.COMPLETED

        except (UnidentifiedImageError, InvalidOperationError) as e:
            logger.error(f"Job {job_id} failed (unrecoverable): {e}")
            job.status = "failed"
            job.error_message = f"Unrecoverable: {e}"
            await session.commit()

            # Metrics: Failure
            await redis_client.incr("metrics:jobs:failed")
            return Outcome.FAILED

        except Exception as e:
            logger.error(f"Job {job_id} failed (transient): {e}")
            job.retry_count += 1

            if job.retry_count < settings.MAX_RETRIES:
                logger.info(f"Job {job_id} scheduling retry {job.retry_count}/{settings.MAX_RETRIES}")
                job.status = "pending"
                job.error_message = str(e)
                await session.commit()
                return Outcome.RETRY

            logger.error(f"Job {job_id} exceeded max retries.")
            job.status = "failed"
            job.error_message = f"Max retries exceeded: {e}"
            await session.commit()

            # Metrics: Failure
            await redis_client.incr("metrics:jobs:failed")
            return Outcome.EXHAUSTED
