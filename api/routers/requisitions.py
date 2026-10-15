"""Fuel requisition routes (submit and history)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import FuelRequestUser, ManageUsersUser
from api.core.dependencies import get_db_path
from api.schemas.auth import MessageResponse
from api.schemas.requisition import (
    CancelApprovedRequest,
    PriorApprovedResponse,
    RequisitionCreateRequest,
    RequisitionResponse,
    RequisitionUpdateRequest,
    RequestFormContextResponse,
)
from api.services import requisition_service

router = APIRouter(prefix="/requisitions", tags=["requisitions"])


def _handle_service_error(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/form-context", response_model=RequestFormContextResponse)
def get_form_context(
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> RequestFormContextResponse:
    """Return vehicles, vendors, and default requestor for the request form."""
    ctx = requisition_service.get_form_context(db_path, user["id"])
    return RequestFormContextResponse(**ctx)


@router.get("/prior-approved/{vehicle_id}", response_model=PriorApprovedResponse)
def get_prior_approved(
    vehicle_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> PriorApprovedResponse:
    """Return prior approved requests for a vehicle (last 2 days)."""
    requests = requisition_service.get_prior_approved(db_path, vehicle_id)
    return PriorApprovedResponse(vehicle_id=vehicle_id, requests=requests)


@router.get("", response_model=List[RequisitionResponse])
def list_my_requisitions(
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> List[RequisitionResponse]:
    """List requisitions submitted by the current user."""
    try:
        rows = requisition_service.list_user_requisitions(db_path, user["id"], user)
        return [RequisitionResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("/{requisition_id}", response_model=RequisitionResponse)
def get_requisition(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> RequisitionResponse:
    """Fetch a single requisition owned by or editable by the user."""
    row = requisition_service.get_requisition(db_path, requisition_id, user["id"], user)
    if not row:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return RequisitionResponse(**row)


@router.post("", response_model=RequisitionResponse, status_code=status.HTTP_201_CREATED)
def create_requisition(
    payload: RequisitionCreateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> RequisitionResponse:
    """Submit a new fuel requisition."""
    try:
        req_id = requisition_service.submit_requisition(
            db_path,
            requester_id=user["id"],
            vehicle_id=payload.vehicle_id,
            vendor_id=payload.vendor_id,
            fuel_type=payload.fuel_type,
            quantity_mode=payload.quantity_mode,
            quantity=payload.quantity,
            notes=payload.notes,
            requestor_name=payload.requestor_name,
            settlement_type=payload.settlement_type,
            actor=user,
            unit_price=payload.unit_price,
        )
        row = requisition_service.get_requisition(db_path, req_id, user["id"], user)
        if not row:
            raise HTTPException(status_code=500, detail="Requisition created but not found")
        return RequisitionResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{requisition_id}", response_model=RequisitionResponse)
def update_requisition_route(
    requisition_id: int,
    payload: RequisitionUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: FuelRequestUser,
) -> RequisitionResponse:
    """Update a pending requisition (one-time edit rules apply; override permission: any status)."""
    try:
        requisition_service.save_requisition(
            db_path,
            requisition_id,
            user["id"],
            user,
            payload.vehicle_id,
            payload.vendor_id,
            payload.fuel_type,
            payload.quantity_mode,
            payload.quantity,
            payload.notes,
            settlement_type=payload.settlement_type,
            actor=user,
            unit_price=payload.unit_price,
        )
        row = requisition_service.get_requisition(
            db_path, requisition_id, user["id"], user
        )
        if not row:
            raise HTTPException(status_code=404, detail="Requisition not found")
        return RequisitionResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{requisition_id}/admin-cancel", response_model=MessageResponse)
def admin_cancel_route(
    requisition_id: int,
    payload: CancelApprovedRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: ManageUsersUser,
) -> MessageResponse:
    """Cancel a request from pending through received (superuser only)."""
    try:
        requisition_service.admin_cancel(
            db_path,
            requisition_id,
            user["id"],
            payload.reason,
            actor=user,
        )
        return MessageResponse(message="Request cancelled")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
