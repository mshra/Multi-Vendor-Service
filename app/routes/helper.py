from pymongo.results import InsertOneResult
from app.queue import get_connection
from typing import Annotated
from app.models import Status
import json
from datetime import datetime, timezone
from fastapi import Depends
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection
from pydantic.types import UUID4
from pymongo.asynchronous.collection import AsyncCollection
from ..mongo import get_collection
from ..logger import log
from .models import JobRequestModel


async def process_job_async(
    req_id: UUID4,
    jobs_queue: Annotated[AbstractRobustConnection, Depends(get_connection)],
    jobs: Annotated[AsyncCollection, Depends(get_collection)],
    job_data: JobRequestModel,
):
    job = {
        "request_id": str(req_id),
        "status": Status.PENDING,
        "created_at": datetime.now(timezone.utc),
        "job_data": job_data.model_dump(),
    }

    result: InsertOneResult | None = None

    try:
        result = await jobs.insert_one(job)
        log.info(f"Job inserted successfully with MongoDB ID: {result.inserted_id}")
    except Exception as e:
        log.error(f"Error while inserting job: {e}")

    try:
        async with jobs_queue:
            channel = await jobs_queue.channel()
            await channel.declare_queue("jobs_queue", durable=True)

            message = Message(
                json.dumps(job, default=str).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
            )

            await channel.default_exchange.publish(message, routing_key="jobs_queue")
            log.info(f"Job published to queue with request_id: {req_id}")
    except Exception as e:
        log.error(f"Error while queueing job: {e}")
        try:
            if result:
                await jobs.delete_one({"_id": result.inserted_id})
                log.info(f"Rolled back job {req_id} from MongoDB")
        except Exception as rollback_error:
            log.error(f"Failed to rollback job {req_id}: {rollback_error}")
