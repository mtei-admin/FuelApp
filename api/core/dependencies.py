"""FastAPI dependencies for database access and authentication."""
from typing import Annotated, Any, Dict, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status

from api.core.config import DB_PATH, SESSION_COOKIE_NAME
from api.core.request_utils import get_client_ip
from src.database import (
    fetch_user_by_id,
    get_user_id_from_session,
    touch_user_session,
)
from src.permissions import build_public_user, effective_permissions


def get_db_path() -> str:
    """Return the SQLite database path."""
    return str(DB_PATH)


def get_current_user_optional(
    request: Request,
    db_path: Annotated[str, Depends(get_db_path)],
    session_token: Annotated[Optional[str], Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> Optional[Dict[str, Any]]:
    """
    Return the authenticated user if a valid session cookie is present.

    Args:
        request: Incoming HTTP request (for client IP on activity touch).
        db_path: SQLite database path.
        session_token: Raw session token from httpOnly cookie.

    Returns:
        User dict without password hash, or None if not authenticated.
    """
    if not session_token:
        return None

    user_id = get_user_id_from_session(db_path, session_token)
    if not user_id:
        return None

    touch_user_session(db_path, session_token, ip_address=get_client_ip(request))

    user = fetch_user_by_id(db_path, user_id)
    if not user or not user.get("is_active"):
        return None

    return build_public_user(user)


def get_current_user(
    user: Annotated[Optional[Dict[str, Any]], Depends(get_current_user_optional)],
) -> Dict[str, Any]:
    """
    Require an authenticated user.

    Raises:
        HTTPException: If the user is not logged in.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def require_roles(*allowed_roles: str):
    """
    Build a dependency that restricts access to specific roles.

    Legacy helper — prefer require_permission for new routes.

    Args:
        allowed_roles: Role names allowed to access the route.

    Returns:
        FastAPI dependency function.
    """

    def _checker(
        user: Annotated[Dict[str, Any], Depends(get_current_user)],
    ) -> Dict[str, Any]:
        role = (user.get("role") or "").lower()
        if role not in {r.lower() for r in allowed_roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker


def require_permission(*required_codes: str):
    """
    Build a dependency that restricts access to users with any listed permission.

    Args:
        required_codes: Permission codes; user needs at least one.

    Returns:
        FastAPI dependency function.
    """

    def _checker(
        user: Annotated[Dict[str, Any], Depends(get_current_user)],
    ) -> Dict[str, Any]:
        granted = set(user.get("permissions") or [])
        if not any(code in granted for code in required_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker


def user_effective_permissions(user: Dict[str, Any], db_path: str) -> set[str]:
    """
    Resolve permissions for a public user or raw DB row.

    Args:
        user: Public user dict or database row.
        db_path: SQLite path when a fresh DB row lookup is required.

    Returns:
        Effective permission code set.
    """
    if user.get("permissions") and "hashed_password" not in user:
        return set(user.get("permissions") or [])
    if "permissions" in user and user.get("permissions") is not None:
        return effective_permissions(user)
    refreshed = fetch_user_by_id(db_path, user["id"])
    if not refreshed:
        return set()
    return effective_permissions(refreshed)
