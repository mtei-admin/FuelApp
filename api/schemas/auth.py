"""Authentication API schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials for login."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """Public user profile returned by the API."""

    id: int
    username: str
    role: str
    permissions: List[str] = Field(default_factory=list)
    full_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    is_active: bool = True


class MessageResponse(BaseModel):
    """Generic success or informational message."""

    message: str
