"""Fleet PMS routes (date due dates and work orders)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import PmsUser
from api.core.dependencies import get_db_path
from api.schemas.pms import (
    PmsScheduleUpdateRequest,
    PmsSummary,
    PmsVehicleResponse,
    PmsWorkOrderResponse,
    PmsWorkOrderWriteRequest,
)
from api.services import pms_service

router = APIRouter(prefix="/pms", tags=["pms"])


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _payload_dict(payload: PmsWorkOrderWriteRequest) -> dict:
    """Dump a write request including nested lines."""
    return payload.model_dump()


@router.get("/summary", response_model=PmsSummary)
def pms_summary_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PmsUser,
) -> PmsSummary:
    """Return due-status counts and open PMS jobs."""
    try:
        return PmsSummary(**pms_service.get_pms_summary(db_path))
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("", response_model=List[PmsVehicleResponse])
def list_pms_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PmsUser,
) -> List[PmsVehicleResponse]:
    """List company-owned vehicles with PMS due status."""
    try:
        rows = pms_service.get_pms_vehicles(db_path)
        return [PmsVehicleResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.put("/schedules/{vehicle_id}", response_model=PmsVehicleResponse)
def update_pms_schedule_route(
    vehicle_id: int,
    payload: PmsScheduleUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PmsUser,
) -> PmsVehicleResponse:
    """Set or clear the date and odometer schedule."""
    try:
        row = pms_service.save_pms_schedule(
            db_path,
            vehicle_id,
            payload.interval_months,
            payload.next_due_date,
            payload.interval_km,
            payload.last_odometer_km,
            actor=user,
        )
        return PmsVehicleResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("/work-orders/{work_order_id}", response_model=PmsWorkOrderResponse)
def get_pms_work_order_route(
    work_order_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PmsUser,
) -> PmsWorkOrderResponse:
    """Return one PMS job with its lines."""
    try:
        return PmsWorkOrderResponse(**pms_service.get_pms_job(db_path, work_order_id))
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/work-orders", response_model=PmsWorkOrderResponse)
def open_pms_work_order_route(
    payload: PmsWorkOrderWriteRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PmsUser,
) -> PmsWorkOrderResponse:
    """Open a PMS job. One open job per vehicle. Lines are optional until complete."""
    try:
        row = pms_service.open_pms_job(db_path, _payload_dict(payload), actor=user)
        return PmsWorkOrderResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.put("/work-orders/{work_order_id}", response_model=PmsWorkOrderResponse)
def update_pms_work_order_route(
    work_order_id: int,
    payload: PmsWorkOrderWriteRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PmsUser,
) -> PmsWorkOrderResponse:
    """Save an open PMS job. Completed jobs stay locked."""
    try:
        row = pms_service.save_pms_job(
            db_path, work_order_id, _payload_dict(payload), actor=user
        )
        return PmsWorkOrderResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/work-orders/{work_order_id}/complete", response_model=PmsWorkOrderResponse)
def complete_pms_work_order_route(
    work_order_id: int,
    payload: PmsWorkOrderWriteRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PmsUser,
) -> PmsWorkOrderResponse:
    """Complete an open PMS job. Doc. date rolls the next due date when an interval is set."""
    try:
        row = pms_service.complete_pms_job(
            db_path,
            work_order_id,
            _payload_dict(payload),
            user.get("id"),
            actor=user,
        )
        return PmsWorkOrderResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/work-orders/{work_order_id}/cancel", response_model=PmsWorkOrderResponse)
def cancel_pms_work_order_route(
    work_order_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: PmsUser,
) -> PmsWorkOrderResponse:
    """Cancel an open PMS job. The due date and odometer chain stay unchanged."""
    try:
        row = pms_service.cancel_pms_job(db_path, work_order_id, actor=user)
        return PmsWorkOrderResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("/vehicles/{vehicle_id}/history", response_model=List[PmsWorkOrderResponse])
def pms_history_route(
    vehicle_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: PmsUser,
) -> List[PmsWorkOrderResponse]:
    """List completed and cancelled PMS jobs for one vehicle."""
    try:
        rows = pms_service.get_pms_history(db_path, vehicle_id)
        return [PmsWorkOrderResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error
