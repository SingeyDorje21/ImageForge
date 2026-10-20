"""Publishes job ids to the configured queue backend.

- "rabbitmq": always-on broker consumed by ``worker.main`` (local dev / docker compose)
- "cloudtasks": Google Cloud Tasks pushing to the HTTP worker in ``worker.server``,
  so nothing runs while there are no jobs
"""
import json
from typing import Protocol

import aio_pika

from api.config import Settings


class JobQueue(Protocol):
    async def publish(self, job_id: str) -> None: ...
    async def close(self) -> None: ...


class RabbitMQQueue:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection = None
        self.channel = None

    async def connect(self) -> "RabbitMQQueue":
        s = self.settings
        self.connection = await aio_pika.connect_robust(s.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(s.DLQ_NAME, durable=True)
        await self.channel.declare_queue(
            s.RETRY_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": s.QUEUE_NAME,
                "x-message-ttl": 5000,
            },
        )
        await self.channel.declare_queue(s.QUEUE_NAME, durable=True)
        return self

    async def publish(self, job_id: str) -> None:
        message = aio_pika.Message(
            body=json.dumps({"job_id": job_id}).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self.channel.default_exchange.publish(message, routing_key=self.settings.QUEUE_NAME)

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()


class CloudTasksQueue:
    def __init__(self, settings: Settings, client=None):
        from google.cloud import tasks_v2

        self.settings = settings
        self.tasks_v2 = tasks_v2
        self.client = client or tasks_v2.CloudTasksAsyncClient()
        self.parent = self.client.queue_path(
            settings.GCP_PROJECT, settings.GCP_LOCATION, settings.CLOUD_TASKS_QUEUE
        )

    async def publish(self, job_id: str) -> None:
        s = self.settings
        url = s.WORKER_URL.rstrip("/") + "/tasks/process"
        http_request = self.tasks_v2.HttpRequest(
            http_method=self.tasks_v2.HttpMethod.POST,
            url=url,
            headers={"Content-Type": "application/json"},
            body=json.dumps({"job_id": job_id}).encode(),
        )
        if s.TASKS_SERVICE_ACCOUNT:
            http_request.oidc_token = self.tasks_v2.OidcToken(
                service_account_email=s.TASKS_SERVICE_ACCOUNT,
                audience=s.WORKER_URL.rstrip("/"),
            )
        await self.client.create_task(
            parent=self.parent, task=self.tasks_v2.Task(http_request=http_request)
        )

    async def close(self) -> None:
        pass


async def create_queue(settings: Settings) -> JobQueue:
    if settings.QUEUE_BACKEND == "cloudtasks":
        return CloudTasksQueue(settings)
    if settings.QUEUE_BACKEND == "rabbitmq":
        return await RabbitMQQueue(settings).connect()
    raise ValueError(f"Unknown QUEUE_BACKEND '{settings.QUEUE_BACKEND}'")
