"""PO release API schemas."""
from pydantic import BaseModel, Field


class ReleaseRequest(BaseModel):
    """Payload to release a PO to the driver."""

    released_date: str = Field(..., min_length=1)
    remarks: str = ""
