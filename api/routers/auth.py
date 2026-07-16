"""Authentication routes: login, logout, current user."""
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from api.core.config import (
    SESSION_COOKIE_NAME,
    get_session_cookie_samesite,
    get_session_cookie_secure,
)
from api.core.dependencies import get_current_user, get_db_path
from api.core.request_utils import get_client_ip
from api.schemas.auth import LoginRequest, MessageResponse, UserResponse
from api.services.auth_service import authenticate_user, logout_user
from src.session_policy import seconds_until_timestamp, workday_session_expires_at

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db_path: Annotated[str, Depends(get_db_path)],
) -> UserResponse:
    """
    Authenticate with username and password; set httpOnly session cookie.

    Args:
        payload: Login credentials.
        response: FastAPI response used to set the session cookie.
        db_path: SQLite database path.

    Returns:
        Authenticated user profile.

    Raises:
        HTTPException: If credentials are invalid.
    """
    user, token, error = authenticate_user(
        db_path,
        payload.username,
        payload.password,
        ip_address=get_client_ip(request),
    )
    if error or not user or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Invalid credentials",
        )

    cookie_secure = get_session_cookie_secure()
    cookie_samesite = get_session_cookie_samesite()
    if cookie_samesite == "none" and not cookie_secure:
        cookie_secure = True

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=seconds_until_timestamp(workday_session_expires_at()),
        samesite=cookie_samesite,
        secure=cookie_secure,
        path="/",
    )
    return UserResponse(**user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    db_path: Annotated[str, Depends(get_db_path)],
    session_token: Annotated[Optional[str], Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> MessageResponse:
    """Invalidate session and clear cookie."""
    logout_user(db_path, session_token)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=get_session_cookie_secure(),
        samesite=get_session_cookie_samesite(),
    )
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def get_me(
    user: Annotated[dict, Depends(get_current_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse(**user)
