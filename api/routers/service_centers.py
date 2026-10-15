"""Service center master data routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import MasterDataUser
from api.core.dependencies import get_db_path
from api.schemas.auth import MessageResponse
from api.schemas.service_center import ServiceCenterResponse, ServiceCenterWriteRequest
from api.services import service_center_service

router = APIRouter(prefix="/service-centers", tags=["service-centers"])


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert a service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _to_response(row: dict) -> ServiceCenterResponse:
    """Map a database row to the API response."""
    return ServiceCenterResponse(
        id=row["id"],
        name=row["name"],
        address=row.get("address") or "",
        contact_no=row.get("contact_no") or "",
        is_active=bool(row.get("is_active")),
        created_at=row.get("created_at"),
    )


def _load_center(db_path: str, service_center_id: int) -> ServiceCenterResponse:
    """Reload one service center after a write."""
    row = next(
        (
            item
            for item in service_center_service.get_all_service_centers(db_path)
            if item["id"] == service_center_id
        ),
        None,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Service center not found")
    return _to_response(row)


@router.get("", response_model=List[ServiceCenterResponse])
def list_service_centers_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> List[ServiceCenterResponse]:
    """List all service centers, including inactive ones."""
    try:
        rows = service_center_service.get_all_service_centers(db_path)
        return [_to_response(row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("", response_model=ServiceCenterResponse, status_code=status.HTTP_201_CREATED)
def create_service_center_route(
    payload: ServiceCenterWriteRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> ServiceCenterResponse:
    """Create a service center."""
    try:
        service_center_id = service_center_service.add_service_center(
            db_path,
            payload.name,
            payload.address,
            payload.contact_no,
            actor=user,
        )
        return _load_center(db_path, service_center_id)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{service_center_id}", response_model=ServiceCenterResponse)
def update_service_center_route(
    service_center_id: int,
    payload: ServiceCenterWriteRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> ServiceCenterResponse:
    """Update a service center's name, address, and contact number."""
    try:
        service_center_service.save_service_center(
            db_path,
            service_center_id,
            payload.name,
            payload.address,
            payload.contact_no,
            actor=user,
        )
        return _load_center(db_path, service_center_id)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{service_center_id}/deactivate", response_model=MessageResponse)
def deactivate_service_center_route(
    service_center_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> MessageResponse:
    """Deactivate a service center."""
    try:
        service_center_service.deactivate_service_center(
            db_path, service_center_id, actor=user
        )
        return MessageResponse(message="Service center deactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{service_center_id}/reactivate", response_model=MessageResponse)
def reactivate_service_center_route(
    service_center_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> MessageResponse:
    """Reactivate a deactivated service center."""
    try:
        service_center_service.restore_service_center(
            db_path, service_center_id, actor=user
        )
        return MessageResponse(message="Service center reactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
