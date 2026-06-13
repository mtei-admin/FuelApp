"""Billing routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.core.dependencies import get_db_path, require_roles
from api.schemas.auth import MessageResponse
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
    invoice_number: str = ""


def _err(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


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
    _user: BillingUser,
) -> MessageResponse:
    """Set actual quantity for FULLTANK item."""
    try:
        billing_service.set_actual_quantity(
            db_path, requisition_id, payload.actual_quantity
        )
        return MessageResponse(message="Actual quantity updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/mark-billed")
def mark_billed(
    payload: MarkBilledRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: BillingUser,
) -> dict:
    """Mark selected items as billed; returns summary for PDF download."""
    try:
        summary = billing_service.mark_billed(
            db_path,
            payload.requisition_ids,
            payload.invoice_number,
        )
        return summary
    except RuntimeError as error:
        raise _err(error) from error
