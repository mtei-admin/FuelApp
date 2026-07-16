"""User administration API schemas (superuser only)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

UserRole = Literal["encoder", "approver", "purchaser", "accounting", "superuser"]


class UserAdminResponse(BaseModel):
    """User record for admin listing."""

    id: int
    username: str
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None


class UserCreateRequest(BaseModel):
    """Payload to enroll a new user."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    role: UserRole = "encoder"
    email: Optional[str] = None
    company: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Payload to update an existing user."""

    username: Optional[str] = Field(None, min_length=1)
    full_name: Optional[str] = Field(None, min_length=1)
    role: Optional[UserRole] = None
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=1)
    company: Optional[str] = None
