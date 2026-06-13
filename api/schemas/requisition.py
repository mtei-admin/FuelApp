"""Requisition API schemas."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

QuantityMode = Literal["numeric", "fulltank"]


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


class RequisitionCreateRequest(BaseModel):
    """Payload to submit a new fuel requisition."""

    vehicle_id: int
    vendor_id: int
    fuel_type: str = Field(..., min_length=1)
    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""
    requestor_name: str = Field(..., min_length=1)


class RequisitionUpdateRequest(BaseModel):
    """Payload to update a pending requisition."""

    vehicle_id: int
    vendor_id: int
    fuel_type: str = Field(..., min_length=1)
    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""


class ApprovalQuantityUpdateRequest(BaseModel):
    """Payload for approvers to edit quantity before approval."""

    quantity_mode: QuantityMode
    quantity: float = 0.0
    notes: str = ""


class PendingRequisitionResponse(RequisitionResponse):
    """Pending requisition with approval display fields."""

    requester_name: Optional[str] = None
    display_total: Optional[float] = None
    can_approve: bool = False


class RequestFormContextResponse(BaseModel):
    """Context data for the new request form."""

    default_requestor_name: str
    vehicles: list
    vendors: list


class PriorApprovedResponse(BaseModel):
    """Prior approved requests warning for a vehicle."""

    vehicle_id: int
    requests: list
