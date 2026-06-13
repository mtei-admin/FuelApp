"""Vendor API schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class VendorResponse(BaseModel):
    """Active vendor record."""

    id: int
    name: str
    address: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class VendorCreateRequest(BaseModel):
    """Payload to create a vendor."""

    name: str = Field(..., min_length=1)
    address: str = ""


class VendorUpdateRequest(BaseModel):
    """Payload to update a vendor."""

    name: str = Field(..., min_length=1)
    address: str = ""
