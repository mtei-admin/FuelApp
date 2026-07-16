"""Company master data API schemas."""
from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    """Company record for master data listing."""

    id: int
    code: str
    name: str
    is_active: bool
    created_at: str | None = None


class CompanyCreateRequest(BaseModel):
    """Payload to create a company."""

    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class CompanyUpdateRequest(BaseModel):
    """Payload to update a company (display name only)."""

    name: str = Field(..., min_length=1)
