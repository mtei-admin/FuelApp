"""Reports routes."""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from api.core.dependencies import get_db_path, require_roles
from api.services import pdf_service, reports_service

router = APIRouter(prefix="/reports", tags=["reports"])

ReportsUser = Annotated[
    dict,
    Depends(require_roles("accounting", "superuser")),
]


@router.get("/summary")
def report_summary(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ReportsUser,
    plate: str = Query("", alias="plate"),
    vendor: str = Query("", alias="vendor"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
) -> dict:
    """Return grouped report data with optional filters."""
    return reports_service.build_report(
        db_path, plate, vendor, from_date, to_date
    )


@router.get("/export/csv")
def export_csv(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: ReportsUser,
    plate: str = Query("", alias="plate"),
    vendor: str = Query("", alias="vendor"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
) -> Response:
    """Download filtered report as CSV."""
    report = reports_service.build_report(
        db_path, plate, vendor, from_date, to_date
    )
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
) -> Response:
    """Download filtered report as PDF."""
    report = reports_service.build_report(
        db_path, plate, vendor, from_date, to_date
    )
    pdf_bytes = pdf_service.build_report_pdf_bytes(
        db_path, report["rows"], report["grand_total"]
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fuel_report.pdf"},
    )
