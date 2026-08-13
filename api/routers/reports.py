"""Reports routes."""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from api.core.dependencies import get_db_path, require_roles
from api.services import pdf_service, reports_service

router = APIRouter(prefix="/reports", tags=["reports"])

ReportsUser = Annotated[
    dict,
    Depends(require_roles("purchaser", "accounting", "superuser")),
]


def _build(
    db_path: str,
    plate: str,
    vendor: str,
    from_date: Optional[date],
    to_date: Optional[date],
    status_filter: str,
) -> dict:
    """Build report or raise HTTP 400 for invalid status filter."""
    try:
        return reports_service.build_report(
            db_path, plate, vendor, from_date, to_date, status_filter
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get("/summary")
def report_summary(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ReportsUser,
    plate: str = Query("", alias="plate"),
    vendor: str = Query("", alias="vendor"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    status_filter: str = Query("", alias="status"),
) -> dict:
    """Return grouped report data with optional filters."""
    return _build(db_path, plate, vendor, from_date, to_date, status_filter)


@router.get("/export/csv")
def export_csv(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ReportsUser,
    plate: str = Query("", alias="plate"),
    vendor: str = Query("", alias="vendor"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    status_filter: str = Query("", alias="status"),
) -> Response:
    """Download filtered report as CSV."""
    report = _build(db_path, plate, vendor, from_date, to_date, status_filter)
    csv_bytes = reports_service.build_report_csv(report["rows"])
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fuel_report.csv"},
    )


@router.get("/export/pdf")
def export_pdf(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ReportsUser,
    plate: str = Query("", alias="plate"),
    vendor: str = Query("", alias="vendor"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    status_filter: str = Query("", alias="status"),
) -> Response:
    """Download filtered report as PDF."""
    report = _build(db_path, plate, vendor, from_date, to_date, status_filter)
    pdf_bytes = pdf_service.build_report_pdf_bytes(
        db_path,
        report["rows"],
        report["grand_total"],
        groups=report.get("groups"),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fuel_report.pdf"},
    )
