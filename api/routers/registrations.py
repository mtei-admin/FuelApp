"""Fleet Registrations / Renewal routes (LTO / OR-CR)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import RegistrationsUpdateUser, RegistrationsViewUser
from api.core.dependencies import get_db_path
from api.schemas.registration import (
    RegistrationResponse,
    RegistrationSummary,
    RegistrationUpdateRequest,
)
from api.services import registration_service

router = APIRouter(prefix="/registrations", tags=["registrations"])


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/summary", response_model=RegistrationSummary)
def registration_summary_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: RegistrationsViewUser,
) -> RegistrationSummary:
    """Return alert counts for active vehicle registrations."""
    try:
        return RegistrationSummary(**registration_service.get_registration_summary(db_path))
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("", response_model=List[RegistrationResponse])
def list_registrations_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: RegistrationsViewUser,
) -> List[RegistrationResponse]:
    """List active vehicles with LTO expiry and OR/CR details."""
    try:
        rows = registration_service.get_registrations(db_path)
        return [RegistrationResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{vehicle_id}", response_model=RegistrationResponse)
def update_registration_route(
    vehicle_id: int,
    payload: RegistrationUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: RegistrationsUpdateUser,
) -> RegistrationResponse:
    """Update LTO / OR-CR fields for one vehicle."""
    try:
        row = registration_service.save_registration(
            db_path,
            vehicle_id,
            lto_expiry=payload.lto_expiry,
            registration_date=payload.registration_date,
            or_number=payload.or_number,
            cr_number=payload.cr_number,
            mv_file_no=payload.mv_file_no,
            registration_remarks=payload.registration_remarks,
            actor=user,
        )
        return RegistrationResponse(**row)
    except RuntimeError as error:
        raise _handle_service_error(error) from error
