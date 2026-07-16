"""User administration routes (superuser / admin only)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.dependencies import get_db_path, require_roles
from api.schemas.auth import MessageResponse
from api.schemas.user_admin import (
    UserAdminResponse,
    UserCreateRequest,
    UserUpdateRequest,
)
from api.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

SuperuserOnly = Annotated[dict, Depends(require_roles("superuser"))]


def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("", response_model=List[UserAdminResponse])
def list_users_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: SuperuserOnly,
) -> List[UserAdminResponse]:
    """List all users for admin enrollment and management."""
    try:
        rows = user_service.get_all_users(db_path)
        return [UserAdminResponse(**row) for row in rows]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def create_user_route(
    payload: UserCreateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: SuperuserOnly,
) -> UserAdminResponse:
    """Enroll a new user."""
    try:
        user_id = user_service.enroll_user(
            db_path,
            payload.username,
            payload.password,
            payload.full_name,
            payload.role,
            payload.email,
            payload.company,
            actor=user,
        )
        rows = user_service.get_all_users(db_path)
        match = next((row for row in rows if row["id"] == user_id), None)
        if not match:
            raise HTTPException(status_code=500, detail="User created but not found")
        return UserAdminResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{user_id}", response_model=UserAdminResponse)
def update_user_route(
    user_id: int,
    payload: UserUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: SuperuserOnly,
) -> UserAdminResponse:
    """Update an existing user."""
    try:
        user_service.save_user(
            db_path,
            user_id,
            username=payload.username,
            full_name=payload.full_name,
            role=payload.role,
            email=payload.email,
            password=payload.password,
            company=payload.company,
            actor=user,
        )
        rows = user_service.get_all_users(db_path)
        match = next((row for row in rows if row["id"] == user_id), None)
        if not match:
            raise HTTPException(status_code=404, detail="User not found")
        return UserAdminResponse(**match)
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user_route(
    user_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    current_user: SuperuserOnly,
) -> MessageResponse:
    """Soft-delete a user account."""
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    try:
        user_service.deactivate_user(db_path, user_id, actor=current_user)
        return MessageResponse(message="User deactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{user_id}/reactivate", response_model=MessageResponse)
def reactivate_user_route(
    user_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: SuperuserOnly,
) -> MessageResponse:
    """Reactivate a deactivated user account."""
    try:
        user_service.activate_user(db_path, user_id, actor=user)
        return MessageResponse(message="User reactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
