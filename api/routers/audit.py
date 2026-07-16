"""Audit trail routes."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query

from api.core.dependencies import get_db_path, require_roles
from api.schemas.audit import AuditLogEntry
from api.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])

AuditUser = Annotated[
    dict,
    Depends(require_roles("accounting", "superuser")),
]


@router.get("", response_model=List[AuditLogEntry])
def list_audit_entries(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: AuditUser,
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> List[AuditLogEntry]:
    """List audit log entries (newest first), optionally filtered by entity."""
    rows = audit_service.get_audit_entries(db_path, entity_type, entity_id, limit)
    return [AuditLogEntry(**row) for row in rows]
