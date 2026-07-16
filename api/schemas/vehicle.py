"""Vehicle (car) API schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.utils.plate import normalize_plate_number

FuelType = Literal["Diesel", "Unleaded Gasoline", "Premium Gasoline"]

FUEL_TYPE_OPTIONS: list[str] = ["Diesel", "Unleaded Gasoline", "Premium Gasoline"]


class VehicleResponse(BaseModel):
    """Active vehicle record."""

    id: int
    plate_number: str
    model: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    fuel_type: Optional[str] = None
    company: Optional[str] = None
    assigned_to: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class VehicleCreateRequest(BaseModel):
    """Payload to create a vehicle."""

    plate_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    fuel_type: FuelType
    company: str = Field(..., min_length=1)
    vendor_id: Optional[int] = None
    assigned_to: str = Field(..., min_length=1)

    @field_validator("plate_number")
    @classmethod
    def validate_plate_number(cls, value: str) -> str:
        """Reject non-alphanumeric plates; store uppercase."""
        return normalize_plate_number(value)


class VehicleUpdateRequest(BaseModel):
    """Payload to update a vehicle."""

    plate_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    fuel_type: FuelType
    company: str = Field(..., min_length=1)
    vendor_id: Optional[int] = None
    assigned_to: str = Field(..., min_length=1)

    @field_validator("plate_number")
    @classmethod
    def validate_plate_number(cls, value: str) -> str:
        """Reject non-alphanumeric plates; store uppercase."""
        return normalize_plate_number(value)
