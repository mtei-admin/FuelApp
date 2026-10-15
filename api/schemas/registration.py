"""Vehicle LTO / OR-CR registration API schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

AlertStatus = Literal["missing", "expired", "due_soon", "current"]


class RegistrationResponse(BaseModel):
    """Active company-owned vehicle with registration fields and alert status."""

    id: int
    plate_number: str
    model: str
    company: Optional[str] = None
    assigned_to: Optional[str] = None
    registration_date: Optional[str] = None
    lto_expiry: Optional[str] = None
    expiration_date: Optional[str] = None
    or_number: Optional[str] = None
    cr_number: Optional[str] = None
    mv_file_no: Optional[str] = None
    registration_remarks: Optional[str] = None
    is_company_owned: bool = True
    alert_status: AlertStatus
    days_until_expiry: Optional[int] = None


class RegistrationUpdateRequest(BaseModel):
    """Payload to update LTO / OR-CR fields for one company-owned vehicle."""

    registration_date: Optional[str] = Field(
        default=None,
        description="Registration date (YYYY-MM-DD); blank clears.",
    )
    lto_expiry: Optional[str] = Field(
        default=None,
        description="Expiration / LTO expiry (YYYY-MM-DD); blank clears.",
    )
    or_number: Optional[str] = None
    cr_number: Optional[str] = None
    mv_file_no: Optional[str] = None
    registration_remarks: Optional[str] = None


class RegistrationSummary(BaseModel):
    """Counts by alert status for the Registrations dashboard strip."""

    total: int
    expired: int
    due_soon: int
    missing: int
    current: int
    due_soon_days: int
