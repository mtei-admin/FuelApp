"""Billing routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.core.dependencies import get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.schemas.cc_fill import ReconcileCcRequest
from api.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])

BillingUser = Annotated[
    dict,
    Depends(require_roles("purchaser", "accounting", "superuser")),
]


class ActualQuantityRequest(BaseModel):
    """Actual quantity for FULLTANK billing."""

    actual_quantity: float = Field(..., gt=0)


class MarkBilledRequest(BaseModel):
    """Batch billing request."""

    requisition_ids: List[int] = Field(..., min_length=1)
    invoice_number: str = Field(..., min_length=1)


class BillingCorrectionRequest(BaseModel):
    """Accounting correction for billed items."""

    requisition_ids: List[int] = Field(..., min_length=1)


class UpdateBillingReferenceRequest(BillingCorrectionRequest):
    """Change billing reference on billed requisitions."""

    invoice_number: str = Field(..., min_length=1)


def _err(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/counts")
def billing_counts_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: BillingUser,
) -> dict:
    """Return queue counts for billing UI badges."""
    return billing_service.get_billing_counts(db_path)


@router.get("/received")
def list_received(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: BillingUser,
) -> List[dict]:
    """List received items awaiting billing."""
    return billing_service.list_received(db_path)


@router.patch("/{requisition_id}/actual-quantity", response_model=MessageResponse)
def update_actual_quantity(
    requisition_id: int,
    payload: ActualQuantityRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: BillingUser,
) -> MessageResponse:
    """Set actual quantity for FULLTANK item."""
    try:
        billing_service.set_actual_quantity(
            db_path, requisition_id, payload.actual_quantity, actor=user
        )
        return MessageResponse(message="Actual quantity updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/mark-billed")
def mark_billed(
    payload: MarkBilledRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: BillingUser,
) -> dict:
    """Mark selected items as billed; returns summary for PDF download."""
    try:
        summary = billing_service.mark_billed(
            db_path,
            payload.requisition_ids,
            payload.invoice_number,
            actor=user,
        )
        return summary
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/billed")
def list_billed(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: BillingUser,
) -> List[dict]:
    """List billed vendor-invoice items (billing corrections)."""
    return billing_service.list_billed(db_path)


@router.post("/update-billing-reference", response_model=MessageResponse)
def update_billing_reference(
    payload: UpdateBillingReferenceRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: BillingUser,
) -> MessageResponse:
    """Change vendor billing reference on billed requisitions."""
    try:
        billing_service.update_billing_reference(
            db_path,
            payload.requisition_ids,
            payload.invoice_number,
            actor=user,
        )
        return MessageResponse(message="Billing reference updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/unbill", response_model=MessageResponse)
def unbill(
    payload: BillingCorrectionRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: BillingUser,
) -> MessageResponse:
    """Remove items from billing (status back to received)."""
    try:
        billing_service.unbill_items(
            db_path,
            payload.requisition_ids,
            actor=user,
        )
        return MessageResponse(message="Item(s) removed from billing")
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/cc-unreconciled")
def list_cc_unreconciled(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: BillingUser,
) -> List[dict]:
    """List paid credit-card fills awaiting statement reconciliation."""
    return billing_service.list_cc_unreconciled(db_path)


@router.post("/reconcile-cc")
def reconcile_cc_route(
    payload: ReconcileCcRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: BillingUser,
) -> dict:
    """Reconcile selected CC fills against a card statement."""
    try:
        return billing_service.reconcile_cc(
            db_path,
            payload.requisition_ids,
            payload.statement_reference,
            actor=user,
        )
    except RuntimeError as error:
        raise _err(error) from error
