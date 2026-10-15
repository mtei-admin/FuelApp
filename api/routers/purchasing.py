"""Purchasing routes: fuel prices, PO generation, receiving."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.core.access import (
    CurrentUser,
    FuelPriceEditUser,
    PurchasingAdminUser,
    PurchasingUser,
    UndoReleaseUser,
)
from api.core.dependencies import get_db_path
from api.schemas.auth import MessageResponse
from api.schemas.cc_fill import RecordCcFillRequest, SettlementTypeUpdateRequest
from api.schemas.receiving import ReceiveRequest
from api.schemas.releasing import ReleaseRequest
from api.services import purchasing_service

router = APIRouter(prefix="/purchasing", tags=["purchasing"])


class FuelPriceUpdateRequest(BaseModel):
    """Fuel price update for one vendor."""

    diesel_price: Optional[float] = None
    unleaded_price: Optional[float] = None
    premium_price: Optional[float] = None


class GeneratePORequest(BaseModel):
    """PO generation payload."""

    unit_price: float = Field(..., gt=0)
    po_reference: str = ""
    signatory_user_id: int = Field(..., gt=0)


class PoSignatoryResponse(BaseModel):
    """User eligible to sign a purchase order PDF."""

    id: int
    full_name: str
    username: Optional[str] = None
    role: Optional[str] = None


class AdminEditRequest(BaseModel):
    """Admin full-edit payload (superuser only)."""

    status: Optional[str] = None
    vehicle_id: Optional[int] = None
    vendor_id: Optional[int] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    fuel_type: Optional[str] = None
    unit_price: Optional[float] = None
    po_reference: Optional[str] = None
    notes: Optional[str] = None
    requestor_name: Optional[str] = None
    actual_unit_price: Optional[float] = None
    actual_quantity: Optional[float] = None
    receipt_number: Optional[str] = None
    received_date: Optional[str] = None
    released_date: Optional[str] = None
    released_by: Optional[str] = None
    release_remarks: Optional[str] = None
    invoice_number: Optional[str] = None
    approved_by: Optional[str] = None
    prepared_by: Optional[str] = None
    po_signatory: Optional[str] = None
    settlement_type: Optional[str] = None
    cc_card_reference: Optional[str] = None
    cc_statement_reference: Optional[str] = None
    cc_reconcile_report_no: Optional[str] = None
    cc_reconciled_at: Optional[str] = None
    cc_reconciled_by: Optional[str] = None
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[str] = None


def _err(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/counts")
def queue_counts_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> dict:
    """Return queue counts for purchasing sidebar badges."""
    return purchasing_service.get_queue_counts(db_path)


@router.get("/fuel-prices")
def list_fuel_prices(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: CurrentUser,
) -> List[dict]:
    """List vendors with current fuel prices (read-only for all authenticated users)."""
    return purchasing_service.list_fuel_prices(db_path)


@router.put("/fuel-prices/{vendor_id}", response_model=MessageResponse)
def update_fuel_prices(
    vendor_id: int,
    payload: FuelPriceUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelPriceEditUser,
) -> MessageResponse:
    """Update fuel prices for a vendor."""
    try:
        purchasing_service.update_fuel_prices(
            db_path,
            vendor_id,
            payload.diesel_price,
            payload.unleaded_price,
            payload.premium_price,
            user["id"],
            actor=user,
        )
        return MessageResponse(message="Prices updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/approved")
def list_approved(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List approved vendor-invoice requisitions awaiting PO."""
    return purchasing_service.list_approved(db_path)


@router.get("/cc-fills")
def list_cc_fills(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List approved credit-card requisitions awaiting fill recording."""
    return purchasing_service.list_cc_fills_approved(db_path)


@router.get("/po-generated")
def list_po_generated(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List PO-generated requisitions awaiting release."""
    return purchasing_service.list_po_generated(db_path)


@router.get("/released")
def list_released(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List released POs awaiting vendor receipt."""
    return purchasing_service.list_released_awaiting_receipt(db_path)


@router.get("/signatories", response_model=List[PoSignatoryResponse])
def list_signatories_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[PoSignatoryResponse]:
    """List active users who may sign POs (approver, accounting, superuser)."""
    rows = purchasing_service.list_signatories(db_path)
    return [PoSignatoryResponse(**row) for row in rows]


@router.post("/{requisition_id}/generate-po", response_model=MessageResponse)
def generate_po(
    requisition_id: int,
    payload: GeneratePORequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Generate PO for an approved requisition."""
    try:
        purchasing_service.generate_po(
            db_path,
            requisition_id,
            payload.unit_price,
            payload.po_reference,
            user["id"],
            payload.signatory_user_id,
            actor=user,
        )
        return MessageResponse(message="PO generated")
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/received")
def list_received(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List received requisitions (editable by purchaser until billed)."""
    return purchasing_service.list_received_awaiting_billing(db_path)


@router.post("/{requisition_id}/release", response_model=MessageResponse)
def release_po_route(
    requisition_id: int,
    payload: ReleaseRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Release PO to driver (po_generated → released)."""
    try:
        purchasing_service.release_po(
            db_path,
            requisition_id,
            user["id"],
            payload.released_date,
            payload.remarks,
            actor=user,
        )
        return MessageResponse(message="PO released")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/undo-release", response_model=MessageResponse)
def undo_release_route(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: UndoReleaseUser,
) -> MessageResponse:
    """Undo release (purchasing.undo_release permission, not yet received)."""
    try:
        purchasing_service.undo_release_po(db_path, requisition_id, actor=user)
        return MessageResponse(message="Release undone")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/received", response_model=MessageResponse)
def mark_received(
    requisition_id: int,
    payload: ReceiveRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Record delivery (released → received; superuser may skip release)."""
    try:
        purchasing_service.save_receiving(
            db_path,
            requisition_id,
            payload.received_date,
            payload.actual_unit_price,
            payload.actual_quantity,
            payload.receipt_number,
            user_role=user.get("role", ""),
            actor=user,
            is_update=False,
            receiving_remarks=payload.remarks,
            user=user,
        )
        return MessageResponse(message="Marked as received")
    except RuntimeError as error:
        raise _err(error) from error


@router.patch("/{requisition_id}/receiving", response_model=MessageResponse)
def update_receiving(
    requisition_id: int,
    payload: ReceiveRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Update delivery details while status is received (before billed)."""
    try:
        purchasing_service.save_receiving(
            db_path,
            requisition_id,
            payload.received_date,
            payload.actual_unit_price,
            payload.actual_quantity,
            payload.receipt_number,
            user_role=user.get("role", ""),
            actor=user,
            is_update=True,
            receiving_remarks=payload.remarks,
            user=user,
        )
        return MessageResponse(message="Receiving updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.patch("/{requisition_id}/settlement-type", response_model=MessageResponse)
def update_settlement_type_route(
    requisition_id: int,
    payload: SettlementTypeUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Change payment method on an approved requisition."""
    try:
        purchasing_service.update_settlement_type(
            db_path,
            requisition_id,
            payload.settlement_type,
            actor=user,
        )
        return MessageResponse(message="Payment method updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/record-cc-fill", response_model=MessageResponse)
def record_cc_fill_route(
    requisition_id: int,
    payload: RecordCcFillRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
) -> MessageResponse:
    """Record credit card fill (approved → paid_cc, skips PO)."""
    try:
        purchasing_service.record_cc_fill_entry(
            db_path,
            requisition_id,
            payload.fill_date,
            payload.actual_unit_price,
            payload.actual_quantity,
            payload.receipt_number,
            payload.cc_card_reference,
            payload.settlement_type,
            actor=user,
        )
        return MessageResponse(message="Credit card fill recorded")
    except RuntimeError as error:
        raise _err(error) from error


@router.patch("/{requisition_id}/admin-edit", response_model=MessageResponse)
def admin_edit_requisition(
    requisition_id: int,
    payload: AdminEditRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingAdminUser,
) -> MessageResponse:
    """Full edit of any requisition field (purchasing.admin_edit, any status)."""
    try:
        purchasing_service.admin_edit(
            db_path, requisition_id, payload.model_dump(exclude_none=True), actor=user
        )
        return MessageResponse(message="Requisition updated")
    except RuntimeError as error:
        raise _err(error) from error
