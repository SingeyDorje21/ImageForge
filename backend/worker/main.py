import asyncio
import json
import logging
import functools

import aio_pika
import redis.asyncio as redis

from api.config import get_settings
from worker.jobs import Outcome, run_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_job(message: aio_pika.IncomingMessage, channel: aio_pika.Channel, redis_client: redis.Redis):
    settings = get_settings()
    exchange = channel.default_exchange

    async def publish(routing_key: str):
        await exchange.publish(
            aio_pika.Message(body=message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )

    async with message.process():
        try:
            body = json.loads(message.body.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Poison message (invalid JSON): {e}")
            await publish(settings.DLQ_NAME)
            return

        job_id = body.get("job_id")
        if not job_id:
            logger.error("No job_id in message. Sending to DLQ.")
            await publish(settings.DLQ_NAME)
            return

        outcome = await run_job(job_id, redis_client)
        if outcome == Outcome.RETRY:
            await publish(settings.RETRY_QUEUE_NAME)
        elif outcome == Outcome.EXHAUSTED:
            await publish(settings.DLQ_NAME)


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
