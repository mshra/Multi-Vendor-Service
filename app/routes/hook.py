from typing import Annotated
from app.logger import log
from typing import Any
from fastapi import Body
from app.models import Status
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.collection import AsyncCollection
from ..mongo import get_collection
from pydantic import BaseModel

router = APIRouter(prefix="/vendor-webhook")


class RequestDataModel(BaseModel):
    request_id: str
    final_data: Any


@router.post(path="/{vendor}")
async def post(
    jobs: Annotated[AsyncCollection, Depends(get_collection)],
    request_data: RequestDataModel = Body(),
):
    request_id = request_data.request_id
    data = request_data.final_data

    try:
        update_result = await jobs.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": Status.COMPLETE,
                    "result": data,
                }
            },
        )

        if update_result.matched_count == 0:
            log.error(f"No job with request_id: {request_id} exists")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No job found with request_id: {request_id}",
            )

        log.info(
            f"Status of job with request_id: {request_id} updated to {Status.COMPLETE}"
        )
    except Exception as e:
        log.error(f"Error updating job with request_id: {request_id} - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
