"""PMS schedule and work-order API schemas."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

PmsAlertStatus = Literal["missing", "overdue", "due_soon", "current"]
WorkOrderStatus = Literal["open", "completed", "cancelled"]
RepairType = Literal["preventive_maintenance", "change_oil", "inspection"]
PaymentTerms = Literal["cash", "15_days", "30_days"]
LineType = Literal["parts", "lubricants", "services", "others"]
LineUnit = Literal["pcs", "liters", "lot", "job"]


class PmsVehicleResponse(BaseModel):
    """Company-owned vehicle with PMS due status and any open job."""

    id: int
    plate_number: str
    model: str
    company: Optional[str] = None
    assigned_to: Optional[str] = None
    interval_months: Optional[int] = None
    next_due_date: Optional[str] = None
    interval_km: Optional[int] = None
    last_odometer_km: Optional[int] = None
    last_service_date: Optional[str] = None
    alert_status: PmsAlertStatus
    days_until_due: Optional[int] = None
    open_work_order_id: Optional[int] = None
    open_work_order_description: Optional[str] = None
    previous_odometer: Optional[int] = None


class PmsSummary(BaseModel):
    """Counts by due status plus open PMS jobs."""

    total: int
    overdue: int
    due_soon: int
    missing: int
    current: int
    open_jobs: int
    due_soon_days: int


class PmsScheduleUpdateRequest(BaseModel):
    """Date and odometer schedule. Blank values clear the field."""

    interval_months: Optional[int] = Field(
        default=None,
        description="Months between services; blank clears.",
    )
    next_due_date: Optional[str] = Field(
        default=None,
        description="Next due date (YYYY-MM-DD); blank clears.",
    )
    interval_km: Optional[int] = Field(
        default=None,
        description="Kilometers between services; blank clears.",
    )
    last_odometer_km: Optional[int] = Field(
        default=None,
        description="Last odometer reading; blank clears.",
    )


class PmsWorkOrderLineInput(BaseModel):
    """One parts or service line. Totals are calculated on the server."""

    part_code: Optional[str] = None
    line_type: LineType
    description: str = Field(..., min_length=1)
    unit: LineUnit
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    discount: float = Field(default=0, ge=0)


class PmsWorkOrderWriteRequest(BaseModel):
    """Header and lines for opening, saving, or completing a PMS job."""

    vehicle_id: int = Field(..., gt=0)
    transaction_no: Optional[str] = None
    doc_date: Optional[str] = None
    repair_type: Optional[RepairType] = None
    service_advisor: Optional[str] = None
    technician: Optional[str] = None
    terms: Optional[PaymentTerms] = None
    shop_name: Optional[str] = None
    remarks: Optional[str] = None
    current_odometer: Optional[int] = Field(default=None, ge=0)
    lines: List[PmsWorkOrderLineInput] = Field(default_factory=list)


class PmsWorkOrderLineResponse(BaseModel):
    """Stored parts or service line."""

    id: int
    work_order_id: int
    line_no: int
    part_code: Optional[str] = None
    line_type: str
    description: str
    unit: str
    quantity: float
    unit_price: float
    discount: float
    total_amount: float


class PmsWorkOrderResponse(BaseModel):
    """One PMS work order, open or historical, with its lines."""

    id: int
    vehicle_id: int
    job_type: str
    status: WorkOrderStatus
    description: Optional[str] = None
    shop_name: Optional[str] = None
    cost: Optional[float] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    opened_at: str
    service_date: Optional[str] = None
    doc_date: Optional[str] = None
    transaction_no: Optional[str] = None
    repair_type: Optional[str] = None
    service_advisor: Optional[str] = None
    technician: Optional[str] = None
    terms: Optional[str] = None
    previous_odometer: Optional[int] = None
    current_odometer: Optional[int] = None
    completed_at: Optional[str] = None
    completed_by_user_id: Optional[int] = None
    completed_by_name: Optional[str] = None
    plate_number: Optional[str] = None
    model: Optional[str] = None
    company: Optional[str] = None
    assigned_to: Optional[str] = None
    lines: List[PmsWorkOrderLineResponse] = Field(default_factory=list)
