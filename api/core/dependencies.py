"""FastAPI dependencies for database access and authentication."""
from typing import Annotated, Any, Dict, Optional

from fastapi import Cookie, Depends, HTTPException, status

from api.core.config import DB_PATH, SESSION_COOKIE_NAME
from src.database import fetch_user_by_id, get_user_id_from_session


def get_db_path() -> str:
    """Return the SQLite database path."""
    return str(DB_PATH)


def get_current_user_optional(
    db_path: Annotated[str, Depends(get_db_path)],
    session_token: Annotated[Optional[str], Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> Optional[Dict[str, Any]]:
    """
    Return the authenticated user if a valid session cookie is present.

    Args:
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

    user = fetch_user_by_id(db_path, user_id)
    if not user or not user.get("is_active"):
        return None

    return _public_user(user)


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


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Strip sensitive fields from a user record."""
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "is_active": bool(user.get("is_active")),
    }
