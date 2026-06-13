"""Dashboard analytics routes."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from api.core.dependencies import get_db_path, require_roles
from api.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DashboardUser = Annotated[
    dict,
    Depends(require_roles("accounting", "superuser")),
]


@router.get("")
def get_dashboard(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    vendor_id: Optional[int] = Query(None),
) -> dict:
    """Return dashboard analytics for the selected month."""
    return dashboard_service.get_dashboard_data(db_path, year, month, vendor_id)
