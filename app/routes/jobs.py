from app.queue import get_connection
from typing import Annotated
from fastapi import BackgroundTasks
from app.models import Status
from app.logger import log
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from aio_pika.abc import AbstractRobustConnection
from pymongo.asynchronous.collection import AsyncCollection
from app.mongo import get_collection
from app.routes.models import JobRequestModel, GetJobStatusResponse, CreateJobResponse
from app.routes.helper import process_job

router = APIRouter(prefix="/jobs")


@router.post(
    path="",
    summary="Create job",
    response_model=CreateJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post(
    jobs_queue: Annotated[AbstractRobustConnection, Depends(get_connection)],
    jobs: Annotated[AsyncCollection, Depends(get_collection)],
    job_data: JobRequestModel,
    background_task: BackgroundTasks,
):
    req_id = uuid.uuid4()

    background_task.add_task(process_job, req_id, jobs_queue, jobs, job_data)

    return CreateJobResponse(request_id=req_id)


@router.get(
    path="/{request_id}", summary="Get job status", status_code=status.HTTP_200_OK
)
async def get(
    request_id: str, jobs: Annotated[AsyncCollection, Depends(get_collection)]
):
    job = await jobs.find_one({"request_id": request_id})

    if job is None:
        log.error(f"job with request_id: {request_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"job with request id {request_id} does not exist",
        )

    job_status: Status = job.get("status")
    job_data = job.get("job_data")

    if job_status == Status.COMPLETE:
        GetJobStatusResponse(status=Status.COMPLETE, result=job_data["data"])

    return GetJobStatusResponse(status=job_status, result=None)
