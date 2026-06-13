"""Vehicle master data routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.dependencies import get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.schemas.vehicle import (
    COMPANY_OPTIONS,
    FUEL_TYPE_OPTIONS,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)
from api.services import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

MasterDataUser = Annotated[dict, Depends(require_roles("approver", "accounting", "superuser"))]


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/options")
def vehicle_options(_user: MasterDataUser) -> dict:
    """Return dropdown options for vehicle forms."""
    return {"fuel_types": FUEL_TYPE_OPTIONS, "companies": COMPANY_OPTIONS}


@router.get("", response_model=List[VehicleResponse])
def list_vehicles_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> List[VehicleResponse]:
    """List active vehicles."""
    try:
        rows = vehicle_service.get_active_vehicles(db_path)
        return [VehicleResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle_route(
    payload: VehicleCreateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> VehicleResponse:
    """Create a new vehicle (or reactivate by plate)."""
    try:
        car_id = vehicle_service.create_vehicle(
            db_path,
            payload.plate_number,
            payload.model,
            payload.fuel_type,
            payload.company,
            payload.vendor_id,
            payload.driver_name,
        )
        rows = vehicle_service.get_active_vehicles(db_path)
        match = next((row for row in rows if row["id"] == car_id), None)
        if not match:
            raise HTTPException(status_code=500, detail="Vehicle created but not found")
        return VehicleResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle_route(
    vehicle_id: int,
    payload: VehicleUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> VehicleResponse:
    """Update an existing vehicle."""
    try:
        vehicle_service.save_vehicle(
            db_path,
            vehicle_id,
            payload.plate_number,
            payload.model,
            payload.fuel_type,
            payload.company,
            payload.vendor_id,
            payload.driver_name,
        )
        rows = vehicle_service.get_active_vehicles(db_path)
        match = next((row for row in rows if row["id"] == vehicle_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return VehicleResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{vehicle_id}/deactivate", response_model=MessageResponse)
def deactivate_vehicle_route(
    vehicle_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> MessageResponse:
    """Soft-delete a vehicle."""
    try:
        vehicle_service.deactivate_vehicle(db_path, vehicle_id)
        return MessageResponse(message="Vehicle deactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
