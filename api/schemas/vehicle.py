"""Vehicle (car) API schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

FuelType = Literal["Diesel", "Unleaded Gasoline", "Premium Gasoline"]
CompanyName = Literal["MTEI", "DSRDC", "DIC", "GCEIC", "MTEI Trucking"]

FUEL_TYPE_OPTIONS: list[str] = ["Diesel", "Unleaded Gasoline", "Premium Gasoline"]
COMPANY_OPTIONS: list[str] = ["MTEI", "DSRDC", "DIC", "GCEIC", "MTEI Trucking"]


class VehicleResponse(BaseModel):
    """Active vehicle record."""

    id: int
    plate_number: str
    model: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    fuel_type: Optional[str] = None
    company: Optional[str] = None
    driver_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class VehicleCreateRequest(BaseModel):
    """Payload to create a vehicle."""

    plate_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    fuel_type: FuelType
    company: CompanyName
    vendor_id: Optional[int] = None
    driver_name: Optional[str] = None


class VehicleUpdateRequest(BaseModel):
    """Payload to update a vehicle."""

    plate_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    fuel_type: FuelType
    company: CompanyName
    vendor_id: Optional[int] = None
    driver_name: Optional[str] = None
