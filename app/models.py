from enum import StrEnum


class Status(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class VendorType(StrEnum):
    SYNC = "sync"
    ASYNC = "async"
