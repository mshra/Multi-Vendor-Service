from app.queue import get_connection
from typing import Annotated
from app.models import Status
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Body, Depends, HTTPException, status
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection
from pydantic.main import BaseModel
from pydantic.types import UUID4
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError
from ..mongo import get_collection
from ..logger import log

router = APIRouter(prefix="/jobs")


class JobsResponseModel(BaseModel):
    request_id: UUID4


@router.post(
    path="/",
    summary="Create job",
    response_model=JobsResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def post(
    jobs_queue: Annotated[AbstractRobustConnection, Depends(get_connection)],
    jobs: Annotated[AsyncCollection, Depends(get_collection)],
    job_data=Body(None),
):
    req_id = uuid.uuid4()

    job = {
        "request_id": str(req_id),
        "status": Status.PENDING,
        "created_at": datetime.now(timezone.utc),
        "job_data": job_data,
    }

    try:
        result = await jobs.insert_one(job)
        log.info(f"Job inserted successfully with MongoDB ID: {result.inserted_id}")
    except PyMongoError as e:
        log.error(f"MongoDB error while inserting job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job",
        )
    except Exception as e:
        log.error(f"Unexpected error while inserting job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

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
        try:
            await jobs.delete_one({"_id": result.inserted_id})
            log.info(f"Rolled back job {req_id} from MongoDB")
        except Exception as rollback_error:
            log.error(f"Failed to rollback job {req_id}: {rollback_error}")

        log.error(f"Error while queueing job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue job",
        )

    return JobsResponseModel(request_id=req_id)


@router.get(
    path="/{request_id}", summary="Get job status", status_code=status.HTTP_200_OK
)
async def get(
    request_id: str, jobs: Annotated[AsyncCollection, Depends(get_collection)]
):
    job = await jobs.find_one({"request_id": request_id})

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"job with request id {request_id} does not exist",
        )

    if job.get("status") == Status.PROCESSING:
        return {"status": Status.PROCESSING}

    return {"status": Status.COMPLETE, "result": ...}
