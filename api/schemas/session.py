"""Active session presence schemas."""
from typing import List, Optional

from pydantic import BaseModel


class ActiveUserResponse(BaseModel):
    """Collapsed active session row for one user."""

    user_id: int
    username: str
    full_name: Optional[str] = None
    role: str
    device_count: int
    is_online: bool
    login_at: str
    last_seen_at: str
    ip_address: str = ""


class ActiveUsersResponse(BaseModel):
    """Active users summary for the dashboard."""

    idle_minutes: int
    online_count: int
    users: List[ActiveUserResponse]
