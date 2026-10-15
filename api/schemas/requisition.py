"""Requisition API schemas."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

QuantityMode = Literal["numeric", "fulltank"]
SettlementType = Literal["vendor_invoice", "credit_card"]


class RequisitionResponse(BaseModel):
    """Fuel requisition record for API responses."""

    id: int
    serial_number: Optional[str] = None
    quantity: float
    unit: str
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    status: str
    notes: Optional[str] = None
    fuel_type: Optional[str] = None
    requestor_name: Optional[str] = None
    created_at: Optional[str] = None
    po_created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_edited: bool = False
    edited_by: Optional[str] = None
    requester_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    vendor_id: Optional[int] = None
    plate_number: Optional[str] = None
    model: Optional[str] = None
    vendor_name: Optional[str] = None
    can_edit: bool = False
    edit_error: Optional[str] = None
    approved_by: Optional[str] = None
    settlement_type: str = "vendor_invoice"

    @field_validator("settlement_type", mode="before")
    @classmethod
    def default_settlement_type(cls, value: object) -> str:
        """Legacy rows may omit settlement_type."""
        if value is None or str(value).strip() == "":
            return "vendor_invoice"
        return str(value).strip().lower()

    @field_validator("edited_by", mode="before")
    @classmethod
    def coerce_edited_by(cls, value: object) -> Optional[str]:
        """edited_by is stored as user id in SQLite; expose as string for API clients."""
        if value is None:
            return None
        return str(value)


class RequisitionCreateRequest(BaseModel):
    """Payload to submit a new fuel requisition."""

    vehicle_id: int
    vendor_id: int
    fuel_type: str = Field(..., min_length=1)
    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""
    requestor_name: str = Field(..., min_length=1)
    settlement_type: SettlementType = "vendor_invoice"
    unit_price: Optional[float] = Field(None, ge=0)


class RequisitionUpdateRequest(BaseModel):
    """Payload to update a pending requisition."""

    vehicle_id: int
    vendor_id: int
    fuel_type: str = Field(..., min_length=1)
    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""
    settlement_type: SettlementType = "vendor_invoice"
    unit_price: Optional[float] = Field(None, ge=0)


class ApprovalQuantityUpdateRequest(BaseModel):
    """Payload for approvers to edit quantity before approval."""

    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""


class CancelApprovedRequest(BaseModel):
    """Payload to cancel an approved request before PO generation."""

    reason: str = Field(..., min_length=10, max_length=500)


class PendingRequisitionResponse(RequisitionResponse):
    """Pending requisition with approval display fields."""

    requester_name: Optional[str] = None
    display_total: Optional[float] = None
    can_approve: bool = False


class RequestFormContextResponse(BaseModel):
    """Context data for the new request form."""

    vehicles: list
    vendors: list


class PriorApprovedResponse(BaseModel):
    """Prior approved requests warning for a vehicle."""

    vehicle_id: int
    requests: list


class VehicleHistoryItem(BaseModel):
    """One row in vehicle-scoped request history."""

    id: int
    serial_number: Optional[str] = None
    quantity: float
    unit: str
    status: str
    fuel_type: Optional[str] = None
    total_price: Optional[float] = None
    created_at: Optional[str] = None
    requestor_name: Optional[str] = None
    vendor_name: Optional[str] = None


class VehicleHistoryResponse(BaseModel):
    """Recent requests for a vehicle."""

    vehicle_id: int
    limit: int
    requests: List[VehicleHistoryItem]
