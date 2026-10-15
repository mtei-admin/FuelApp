"""Service center master data API schemas."""
from pydantic import BaseModel, Field


class ServiceCenterResponse(BaseModel):
    """Service center record for the Master Data list."""

    id: int
    name: str
    address: str
    contact_no: str
    is_active: bool
    created_at: str | None = None


class ServiceCenterWriteRequest(BaseModel):
    """Payload to create or update a service center."""

    name: str = Field(..., min_length=1)
    address: str = ""
    contact_no: str = ""
