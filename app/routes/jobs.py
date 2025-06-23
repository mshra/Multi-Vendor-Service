from enum import StrEnum
from typing import Annotated
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic.main import BaseModel
from pydantic.types import UUID4
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError
from ..mongo import get_collection
from ..logger import log

router = APIRouter(prefix="/jobs")


class Status(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobsResponseModel(BaseModel):
    request_id: UUID4

@router.post(path="/", summary="", response_model=JobsResponseModel)
async def post(jobs: Annotated[AsyncCollection, Depends(get_collection)], job_data=Body(None)):
    req_id = uuid.uuid4()

    # add the job to rabbit mq
    job = {
        "request_id": str(req_id),
        "status": Status.PROCESSING,
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
            detail="Failed to create job"
        )
    except Exception as e:
        log.error(f"Unexpected error while creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

    return JobsResponseModel(request_id=req_id)

@router.get(path="/{request_id}", summary="")
async def get(request_id: str,jobs: Annotated[AsyncCollection, Depends(get_collection)]):
    job = await jobs.find_one({ "request_id": request_id})

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"job with request id {request_id} does not exist")

    if job.get("status") == Status.PROCESSING:
        return {"status": Status.PROCESSING}
