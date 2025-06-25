import asyncio
from urllib.parse import urljoin
from fastapi.encoders import jsonable_encoder
import json
import httpx
from aio_pika import connect_robust
from aio_pika.abc import AbstractIncomingMessage
from app.config import settings
from app.logger import log
from app.mongo import get_collection, start_mongo, close_mongo
from app.models import Status


async def handle_message(message: AbstractIncomingMessage):
    async with message.process():
        try:
            body = message.body.decode()
            data = json.loads(body)
            request_id = data.get("request_id")

            if not request_id:
                log.warning("No request_id found in message")
                return

            collection = get_collection()

            await collection.update_one(
                {"request_id": request_id}, {"$set": {"status": Status.PROCESSING}}
            )
            updated_job = await collection.find_one(
                {"request_id": request_id}, {"_id": 0}
            )
            job_data = updated_job.get("job_data")
            vendor_type = job_data.get("vendor_type")

            if vendor_type == "sync":
                url = urljoin(settings.MOCK_VENDOR_URL, "/vendor/sync")
                # url = urljoin("http://localhost:8001", "/vendor/sync")

                updated_job_dict = jsonable_encoder(updated_job)
                response = httpx.post(url, json=updated_job_dict)

                if response.status_code == 200:
                    await collection.update_one(
                        {"request_id": request_id},
                        {"$set": {"status": Status.COMPLETE}},
                    )
                else:
                    await collection.update_one(
                        {"request_id": request_id}, {"$set": {"status": Status.FAILED}}
                    )
            elif vendor_type == "async":
                url = urljoin(settings.MOCK_VENDOR_URL, "/vendor/async")
                # url = urljoin("http://localhost:8001", "/vendor/async")
                updated_job_dict = jsonable_encoder(updated_job)
                response = httpx.post(url, json=updated_job_dict)

                if response.status_code != 202:
                    await collection.update_one(
                        {"request_id": request_id}, {"$set": {"status": Status.FAILED}}
                    )
            else:
                ...
        except Exception as e:
            log.error(f"Error processing message: {e}")


async def main():
    await start_mongo()

    try:
        connection = await connect_robust(settings.RabbitMQ_URL)
        channel = await connection.channel()

        queue = await channel.declare_queue("jobs_queue", durable=True)

        await queue.consume(handle_message)

        await asyncio.Future()
    finally:
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(main())
