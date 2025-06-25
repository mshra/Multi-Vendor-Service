import asyncio
import signal
import json
from urllib.parse import urljoin
from fastapi.encoders import jsonable_encoder
from aio_pika import connect_robust
from tenacity import retry, stop_after_attempt, wait_exponential
from aio_pika.abc import AbstractIncomingMessage
import httpx

from app.config import settings
from app.logger import log
from app.mongo import get_collection, start_mongo, close_mongo
from app.models import Status


# Graceful shutdown trigger
shutdown_event = asyncio.Event()


# Signal handling
def _shutdown(*_):
    log.info("Shutdown signal received")
    shutdown_event.set()


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _shutdown)


def clean_response(data: dict) -> dict:
    """Trim strings and remove potential PII."""
    cleaned = {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}
    # Remove example PII fields
    for key in ["ssn", "email", "phone"]:
        cleaned.pop(key, None)
    return cleaned


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
async def post_to_vendor(url: str, payload: dict):
    """Retry logic for posting to vendors."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        return response


async def handle_message(message: AbstractIncomingMessage):
    async with message.process():
        try:
            body = message.body.decode()
            data = json.loads(body)
            request_id = data.get("request_id")

            if not request_id:
                log.warning("No request_id in message")
                return

            collection = get_collection()

            await collection.update_one(
                {"request_id": request_id}, {"$set": {"status": Status.PROCESSING}}
            )
            log.info(
                f"Status of job with request_id: {request_id} updated to {Status.PROCESSING}"
            )

            updated_job = await collection.find_one(
                {"request_id": request_id}, {"_id": 0}
            )
            job_data = updated_job.get("job_data")
            vendor = job_data.get("vendor")

            url_path = f"/vendor/{vendor}"
            url = urljoin(settings.MOCK_VENDOR_URL, url_path)
            payload = jsonable_encoder(updated_job)

            async with settings.vendor_rate_limits[vendor]:
                response = await post_to_vendor(url, payload)

            if vendor == "sync":
                if response.status_code == 200:
                    cleaned = clean_response(response.json())
                    await collection.update_one(
                        {"request_id": request_id},
                        {"$set": {"status": Status.COMPLETE, "data": cleaned}},
                    )
                    log.info(
                        f"Status of job with request_id: {request_id} updated to {Status.COMPLETE}"
                    )
                else:
                    await collection.update_one(
                        {"request_id": request_id}, {"$set": {"status": Status.FAILED}}
                    )
                    log.info(
                        f"Status of job with request_id: {request_id} updated to {Status.FAILED}"
                    )
            elif vendor == "async":
                if response.status_code != 202:
                    await collection.update_one(
                        {"request_id": request_id}, {"$set": {"status": Status.FAILED}}
                    )
                    log.info(f"Status of job with request_id: {request_id} updated to {Status.FAILED}")
        except Exception as e:
            log.exception(f"Error processing message: {e}")


async def main():
    await start_mongo()

    connection = await connect_robust(settings.RabbitMQ_URL)
    channel = await connection.channel()

    queue = await channel.declare_queue("jobs_queue", durable=True)

    await queue.consume(lambda msg: asyncio.create_task(handle_message(msg)))

    log.info("Worker started...")
    await shutdown_event.wait()

    log.info("Worker shutting down...")
    await close_mongo()
    await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
