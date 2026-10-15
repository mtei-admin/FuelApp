"""Dashboard card routes."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.core.access import ActiveUsersUser, DashboardUser
from api.core.dependencies import get_db_path
from api.schemas.session import ActiveUsersResponse
from api.services import dashboard_service, session_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_DASHBOARD_SCOPES = frozenset({"all", "used", "cancelled"})


def _empty_to_none(value: Optional[str]) -> Optional[str]:
    """Treat blank query params as unset."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_scope(scope: str) -> str:
    """Normalize and validate All / Used / Cancelled list scope."""
    normalized = (scope or "all").strip().lower()
    if normalized not in _DASHBOARD_SCOPES:
        raise HTTPException(status_code=400, detail="Invalid dashboard scope.")
    return normalized


@router.get("/active-users", response_model=ActiveUsersResponse)
def get_active_users(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ActiveUsersUser,
) -> ActiveUsersResponse:
    """List collapsed active sessions for superuser dashboard oversight."""
    data = session_service.get_collapsed_active_users(db_path)
    return ActiveUsersResponse(**data)


@router.get("/summary")
def dashboard_summary(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
) -> dict:
    """Return the nine Dashboard card counts and filter options."""
    return dashboard_service.summary(db_path)


@router.get("/analytics")
def dashboard_analytics(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    vendor_id: Optional[int] = Query(None),
) -> dict:
    """Price trend and top-10 consuming vehicles per company."""
    return dashboard_service.analytics(db_path, year, month, vendor_id=vendor_id)


@router.get("")
def dashboard_root(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
) -> dict:
    """Same payload as /summary (card counts)."""
    return dashboard_service.summary(db_path)


@router.get("/vehicles")
def dashboard_vehicles(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
    company: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    fuel_type: Optional[str] = Query(None),
) -> List[dict]:
    """Vehicles modal list."""
    return dashboard_service.list_vehicles(
        db_path,
        company=_empty_to_none(company),
        vendor_id=vendor_id,
        fuel_type=_empty_to_none(fuel_type),
    )


@router.get("/vendors")
def dashboard_vendors(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
) -> List[dict]:
    """Vendors modal list."""
    return dashboard_service.list_vendor_rows(db_path)


@router.get("/companies")
def dashboard_companies(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
) -> List[dict]:
    """Companies modal list."""
    return dashboard_service.list_company_rows(db_path)


@router.get("/requests")
def dashboard_requests(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
    scope: str = Query("all"),
    plate: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    company: Optional[str] = Query(None),
    fuel_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    cancelled_from: Optional[str] = Query(None),
    cancelled_to: Optional[str] = Query(None),
) -> List[dict]:
    """All / used / cancelled requests modal list."""
    return dashboard_service.list_requests(
        db_path,
        scope=_parse_scope(scope),
        plate=_empty_to_none(plate),
        vendor_id=vendor_id,
        company=_empty_to_none(company),
        fuel_type=_empty_to_none(fuel_type),
        date_from=_empty_to_none(date_from),
        date_to=_empty_to_none(date_to),
        cancelled_from=_empty_to_none(cancelled_from),
        cancelled_to=_empty_to_none(cancelled_to),
    )


@router.get("/pos")
def dashboard_pos(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DashboardUser,
    scope: str = Query("all"),
    plate: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    company: Optional[str] = Query(None),
    fuel_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    cancelled_from: Optional[str] = Query(None),
    cancelled_to: Optional[str] = Query(None),
) -> List[dict]:
    """All / used / cancelled purchase orders modal list."""
    return dashboard_service.list_purchase_orders(
        db_path,
        scope=_parse_scope(scope),
        plate=_empty_to_none(plate),
        vendor_id=vendor_id,
        company=_empty_to_none(company),
        fuel_type=_empty_to_none(fuel_type),
        date_from=_empty_to_none(date_from),
        date_to=_empty_to_none(date_to),
        cancelled_from=_empty_to_none(cancelled_from),
        cancelled_to=_empty_to_none(cancelled_to),
    )
