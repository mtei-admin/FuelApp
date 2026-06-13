"""Vendor master data routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.dependencies import get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.schemas.vendor import VendorCreateRequest, VendorResponse, VendorUpdateRequest
from api.services import vendor_service

router = APIRouter(prefix="/vendors", tags=["vendors"])

MasterDataUser = Annotated[dict, Depends(require_roles("approver", "accounting", "superuser"))]


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("", response_model=List[VendorResponse])
def list_vendors_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> List[VendorResponse]:
    """List active vendors."""
    try:
        rows = vendor_service.get_active_vendors(db_path)
        return [VendorResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor_route(
    payload: VendorCreateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> VendorResponse:
    """Create a new vendor (or reactivate by name)."""
    try:
        vendor_id = vendor_service.create_vendor(db_path, payload.name, payload.address)
        rows = vendor_service.get_active_vendors(db_path)
        match = next((row for row in rows if row["id"] == vendor_id), None)
        if not match:
            raise HTTPException(status_code=500, detail="Vendor created but not found")
        return VendorResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{vendor_id}", response_model=VendorResponse)
def update_vendor_route(
    vendor_id: int,
    payload: VendorUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> VendorResponse:
    """Update an existing vendor."""
    try:
        vendor_service.save_vendor(db_path, vendor_id, payload.name, payload.address)
        rows = vendor_service.get_active_vendors(db_path)
        match = next((row for row in rows if row["id"] == vendor_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return VendorResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{vendor_id}/deactivate", response_model=MessageResponse)
def deactivate_vendor_route(
    vendor_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> MessageResponse:
    """Soft-delete a vendor."""
    try:
        vendor_service.deactivate_vendor(db_path, vendor_id)
        return MessageResponse(message="Vendor deactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
