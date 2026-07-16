"""Approval routes for pending fuel requisitions."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.dependencies import get_current_user, get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.schemas.requisition import (
    ApprovalQuantityUpdateRequest,
    CancelApprovedRequest,
    PendingRequisitionResponse,
    VehicleHistoryResponse,
)
from api.services import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])

ViewApprovalsUser = Annotated[
    dict,
    Depends(require_roles("approver", "purchaser", "accounting", "superuser")),
]
ApproveUser = Annotated[
    dict,
    Depends(require_roles("approver", "accounting", "superuser")),
]


def _handle_service_error(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/pending/count")
def pending_count_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ViewApprovalsUser,
) -> dict:
    """Return pending approval count for sidebar badge."""
    return {"count": approval_service.pending_count(db_path)}


@router.get("/vehicle-history/{vehicle_id}", response_model=VehicleHistoryResponse)
def vehicle_history_route(
    vehicle_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ViewApprovalsUser,
    limit: int = 10,
) -> VehicleHistoryResponse:
    """Return recent requisitions for a vehicle (newest first, all statuses)."""
    rows = approval_service.list_vehicle_history(db_path, vehicle_id, limit=limit)
    return VehicleHistoryResponse(vehicle_id=vehicle_id, limit=limit, requests=rows)


@router.get("/pending", response_model=List[PendingRequisitionResponse])
def list_pending_route(
    db_path: Annotated[str, Depends(get_db_path)],
    user: ViewApprovalsUser,
) -> List[PendingRequisitionResponse]:
    """List pending requisitions for approval queue."""
    try:
        rows = approval_service.list_pending(db_path, user["role"])
        return [PendingRequisitionResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("/approved-awaiting-po", response_model=List[PendingRequisitionResponse])
def list_approved_awaiting_po_route(
    db_path: Annotated[str, Depends(get_db_path)],
    user: ApproveUser,
) -> List[PendingRequisitionResponse]:
    """List approved requisitions that can still be cancelled (approver roles only)."""
    try:
        rows = approval_service.list_approved_awaiting_po(db_path)
        return [PendingRequisitionResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{requisition_id}/approve", response_model=MessageResponse)
def approve_route(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: ApproveUser,
) -> MessageResponse:
    """Approve a pending requisition."""
    try:
        approval_service.approve_requisition(db_path, requisition_id, user["id"], actor=user)
        return MessageResponse(message="Request approved")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{requisition_id}/reject", response_model=MessageResponse)
def reject_route(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: ApproveUser,
) -> MessageResponse:
    """Reject a pending requisition."""
    try:
        approval_service.reject_requisition(db_path, requisition_id, user["id"], actor=user)
        return MessageResponse(message="Request rejected")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{requisition_id}/cancel", response_model=MessageResponse)
def cancel_approved_route(
    requisition_id: int,
    payload: CancelApprovedRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: ApproveUser,
) -> MessageResponse:
    """Cancel an approved requisition before PO generation (reason required)."""
    try:
        approval_service.cancel_approved(
            db_path,
            requisition_id,
            user["id"],
            payload.reason,
            actor=user,
        )
        return MessageResponse(message="Request cancelled")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{requisition_id}/quantity", response_model=MessageResponse)
def update_quantity_route(
    requisition_id: int,
    payload: ApprovalQuantityUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: ApproveUser,
) -> MessageResponse:
    """Edit quantity on a pending requisition before approval."""
    try:
        approval_service.update_pending_quantity(
            db_path,
            requisition_id,
            user["id"],
            user["role"],
            payload.quantity_mode,
            payload.quantity,
            payload.notes,
            actor=user,
        )
        return MessageResponse(message="Quantity updated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
