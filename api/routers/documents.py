"""Document download routes (PDF)."""
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from api.core.dependencies import get_db_path, require_roles
from api.services import pdf_service

router = APIRouter(prefix="/documents", tags=["documents"])

DocUser = Annotated[
    dict,
    Depends(require_roles("purchaser", "accounting", "superuser")),
]


class BilledSummaryRequest(BaseModel):
    """Context for billed PO summary PDF."""

    invoice_number: str = ""
    billing_date: str = ""
    items: list


@router.get("/po/{requisition_id}")
def download_po_pdf(
    requisition_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    _user: DocUser,
) -> Response:
    """Download purchase order PDF for a requisition."""
    try:
        pdf_bytes = pdf_service.build_po_pdf_bytes(db_path, requisition_id)
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
    name = payload.invoice_number or "no_invoice"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Billed_PO_Summary_{name}.pdf"
        },
    )
