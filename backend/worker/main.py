import asyncio
import json
import logging
import os
import functools
import time

import aio_pika
import redis.asyncio as redis
from sqlalchemy import select
from PIL import UnidentifiedImageError

from api.config import get_settings
from shared.database import async_session_maker
from shared.models import Job
from worker.processor import process_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_job(message: aio_pika.IncomingMessage, channel: aio_pika.Channel, redis_client: redis.Redis):
    settings = get_settings()
    exchange = channel.default_exchange

    async with message.process():
        try:
            body = json.loads(message.body.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Poison message (invalid JSON): {e}")
            await exchange.publish(
                aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=settings.DLQ_NAME
            )
            return

        job_id = body.get("job_id")
        if not job_id:
            logger.error("No job_id in message. Sending to DLQ.")
            await exchange.publish(
                aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=settings.DLQ_NAME
            )
            return

        logger.info(f"Processing job {job_id}")
        start_time = time.time()
        
        async with async_session_maker() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalars().first()
            if not job:
                logger.error(f"Job {job_id} not found in DB")
                return

            job.status = "processing"
            await session.commit()
            await session.refresh(job)

            original_path = job.original_path
            result_dir = os.path.join(settings.STORAGE_PATH, "results")
            ext = os.path.splitext(original_path)[1]

            try:
                result_path = await asyncio.to_thread(
                    process_image,
                    original_path=original_path,
                    result_dir=result_dir,
                    job_id=str(job.id),
                    ext=ext,
                    operations=job.operations,
                )

                job.result_path = result_path
                job.status = "completed"
                await session.commit()
                logger.info(f"Job {job_id} completed successfully")
                
                # Metrics: Success
                await redis_client.incr("metrics:jobs:completed")
                duration = time.time() - start_time
                await redis_client.incrbyfloat("metrics:jobs:total_time_sec", duration)

            except UnidentifiedImageError as e:
                logger.error(f"Job {job_id} failed (unrecoverable): {e}")
                job.status = "failed"
                job.error_message = f"Unrecoverable: {e}"
                await session.commit()
                
                # Metrics: Failure
                await redis_client.incr("metrics:jobs:failed")

            except Exception as e:
                logger.error(f"Job {job_id} failed (transient): {e}")
                job.retry_count += 1
                
                if job.retry_count < settings.MAX_RETRIES:
                    logger.info(f"Job {job_id} scheduling retry {job.retry_count}/{settings.MAX_RETRIES}")
                    job.status = "pending"
                    job.error_message = str(e)
                    await session.commit()
                    
                    await exchange.publish(
                        aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                        routing_key=settings.RETRY_QUEUE_NAME
                    )
                else:
                    logger.error(f"Job {job_id} exceeded max retries. Sending to DLQ.")
                    job.status = "failed"
                    job.error_message = f"Max retries exceeded: {e}"
                    await session.commit()
                    
                    await exchange.publish(
                        aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                        routing_key=settings.DLQ_NAME
                    )
                    # Metrics: Failure
                    await redis_client.incr("metrics:jobs:failed")


async def main():
    settings = get_settings()
    logger.info("Connecting to RabbitMQ...")
    
    connection = None
    for _ in range(10):
        try:
            connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            break
        except Exception as e:
            logger.warning(f"Failed to connect to RabbitMQ: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            
    if not connection:
        logger.error("Could not connect to RabbitMQ after 10 attempts.")
        return
        
    logger.info("Connecting to Redis...")
    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        
        await channel.declare_queue(settings.DLQ_NAME, durable=True)
        await channel.declare_queue(
            settings.RETRY_QUEUE_NAME, 
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": settings.QUEUE_NAME,
                "x-message-ttl": 5000,
            }
        )
        queue = await channel.declare_queue(settings.QUEUE_NAME, durable=True)
        
        logger.info(f"Listening on queue {settings.QUEUE_NAME}")
        
        await queue.consume(functools.partial(process_job, channel=channel, redis_client=redis_client))
        
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
