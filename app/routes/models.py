from typing import Any, Optional
from app.models import Status, VendorType
from pydantic.main import BaseModel
from pydantic.types import UUID4


class CreateJobResponse(BaseModel):
    request_id: UUID4


class JobRequestModel(BaseModel):
    vendor: VendorType
    data: dict = {}


class GetJobStatusResponse(BaseModel):
    status: Status
    result: Optional[Any]
