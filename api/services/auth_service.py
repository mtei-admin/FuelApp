"""Authentication service — login, logout, session management."""
from typing import Any, Dict, Optional, Tuple

from api.core.security import verify_password
from src.database import (
    create_user_session,
    delete_user_session,
    fetch_user_by_username,
)


def authenticate_user(
    db_path: str,
    username: str,
    password: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Validate credentials and create a session token.

    Args:
        db_path: SQLite database path.
        username: Login username.
        password: Plain-text password.

    Returns:
        Tuple of (public_user, session_token, error_message).
        On failure, user and token are None and error_message is set.
    """
    user = fetch_user_by_username(db_path, username.strip())
    if not user or not user.get("is_active"):
        return None, None, "Invalid credentials or inactive account."

    hashed_password = user.get("hashed_password", "")
    if not verify_password(password, hashed_password):
        return None, None, "Invalid credentials or inactive account."

    token = create_user_session(db_path, user["id"])
    public_user = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "is_active": bool(user.get("is_active")),
    }
    return public_user, token, None


def logout_user(db_path: str, session_token: Optional[str]) -> None:
    """
    Invalidate the user's session token.

    Args:
        db_path: SQLite database path.
        session_token: Raw session token from cookie.
    """
    if session_token:
        delete_user_session(db_path, session_token)
