"""Purchasing routes: fuel prices, PO generation, receiving."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.core.dependencies import get_current_user, get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.services import purchasing_service

router = APIRouter(prefix="/purchasing", tags=["purchasing"])

PurchasingUser = Annotated[
    dict,
    Depends(require_roles("purchaser", "accounting", "superuser")),
]


class FuelPriceUpdateRequest(BaseModel):
    """Fuel price update for one vendor."""

    diesel_price: Optional[float] = None
    unleaded_price: Optional[float] = None
    premium_price: Optional[float] = None


class GeneratePORequest(BaseModel):
    """PO generation payload."""

    unit_price: float = Field(..., gt=0)
    po_reference: str = ""


def _err(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/fuel-prices")
def list_fuel_prices(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List vendors with current fuel prices."""
    return purchasing_service.list_fuel_prices(db_path)


@router.put("/fuel-prices/{vendor_id}", response_model=MessageResponse)
def update_fuel_prices(
    vendor_id: int,
    payload: FuelPriceUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PurchasingUser,
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
        )
        return MessageResponse(message="Prices updated")
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/approved")
def list_approved(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List approved requisitions awaiting PO."""
    return purchasing_service.list_approved(db_path)


@router.get("/po-generated")
def list_po_generated(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> List[dict]:
    """List PO-generated requisitions awaiting receipt."""
    return purchasing_service.list_po_generated(db_path)


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
        )
        return MessageResponse(message="PO generated")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/received", response_model=MessageResponse)
def mark_received(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PurchasingUser,
) -> MessageResponse:
    """Mark PO-generated requisition as received."""
    try:
        purchasing_service.mark_received(db_path, requisition_id)
        return MessageResponse(message="Marked as received")
    except RuntimeError as error:
        raise _err(error) from error
