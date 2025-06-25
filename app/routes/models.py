from app.models import VendorType
from pydantic.main import BaseModel
from pydantic.types import UUID4


class JobsResponseModel(BaseModel):
    request_id: UUID4


class JobRequestModel(BaseModel):
    vendor_type: VendorType
    data: dict = {}
