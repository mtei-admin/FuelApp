"""Audit trail API schemas."""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    """One immutable audit log row."""

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    actor_name: Optional[str] = None
    old_values: Dict[str, Any] = {}
    new_values: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    entity_label: Optional[str] = None
