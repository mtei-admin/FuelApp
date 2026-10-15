"""Document download routes (PDF)."""
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from api.core.access import PurchasingUser as DocUser
from api.core.dependencies import get_db_path
from api.services import pdf_service

router = APIRouter(prefix="/documents", tags=["documents"])

class BilledSummaryRequest(BaseModel):
    """Context for billed PO summary PDF."""

    invoice_number: str = ""
    billing_date: str = ""
    items: list


class CcReconcileSummaryRequest(BaseModel):
    """Context for CC reconciliation summary PDF/Excel."""

    report_number: str = ""
    statement_reference: str = ""
    reconciled_date: str = ""
    items: list


@router.get("/po/{requisition_id}")
def download_po_pdf(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: DocUser,
) -> Response:
    """Download purchase order PDF for a requisition."""
    try:
        downloader_name = user.get("full_name") or user.get("username") or ""
        pdf_bytes = pdf_service.build_po_pdf_bytes(db_path, requisition_id, downloader_name)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=PO_{requisition_id}.pdf"
        },
    )


@router.post("/billed-summary")
def download_billed_summary(
    payload: BilledSummaryRequest,
    _user: DocUser,
) -> Response:
    """Download billed PO summary PDF."""
    context: Dict[str, Any] = {
        "invoice_number": payload.invoice_number,
        "billing_date": payload.billing_date,
        "items": payload.items,
    }
    pdf_bytes = pdf_service.build_billed_summary_pdf_bytes(context)
    name = pdf_service.billed_summary_download_stem(payload.invoice_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Billed_PO_Summary_{name}.pdf"
        },
    )


@router.post("/billed-summary-xlsx")
def download_billed_summary_xlsx(
    payload: BilledSummaryRequest,
    _user: DocUser,
) -> Response:
    """Download billed PO summary Excel (.xlsx)."""
    context: Dict[str, Any] = {
        "invoice_number": payload.invoice_number,
        "billing_date": payload.billing_date,
        "items": payload.items,
    }
    try:
        xlsx_bytes = pdf_service.build_billed_summary_xlsx_bytes(context)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to build Excel summary: {error}",
        ) from error
    name = pdf_service.billed_summary_download_stem(payload.invoice_number)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=Billed_PO_Summary_{name}.xlsx"
        },
    )


@router.post("/cc-reconcile-summary")
def download_cc_reconcile_summary(
    payload: CcReconcileSummaryRequest,
    _user: DocUser,
) -> Response:
    """Download CC reconciliation summary PDF."""
    context: Dict[str, Any] = {
        "report_number": payload.report_number,
        "statement_reference": payload.statement_reference,
        "reconciled_date": payload.reconciled_date,
        "items": payload.items,
    }
    pdf_bytes = pdf_service.build_cc_reconcile_summary_pdf_bytes(context)
    name = pdf_service.cc_reconcile_download_stem(payload.report_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=CC_Reconcile_Summary_{name}.pdf"
        },
    )


@router.post("/cc-reconcile-summary-xlsx")
def download_cc_reconcile_summary_xlsx(
    payload: CcReconcileSummaryRequest,
    _user: DocUser,
) -> Response:
    """Download CC reconciliation summary Excel (.xlsx)."""
    context: Dict[str, Any] = {
        "report_number": payload.report_number,
        "statement_reference": payload.statement_reference,
        "reconciled_date": payload.reconciled_date,
        "items": payload.items,
    }
    try:
        xlsx_bytes = pdf_service.build_cc_reconcile_summary_xlsx_bytes(context)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to build Excel summary: {error}",
        ) from error
    name = pdf_service.cc_reconcile_download_stem(payload.report_number)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=CC_Reconcile_Summary_{name}.xlsx"
        },
    )
