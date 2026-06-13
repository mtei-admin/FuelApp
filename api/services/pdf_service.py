"""PDF generation helpers for API document downloads."""
from typing import Any, Dict, Optional

from src.modules.purchasing import build_po_pdf
from src.database import fetch_requisition_by_id, list_requisitions_by_status
from src.utils.pdf_gen import generate_billed_summary_pdf, generate_report_pdf


def build_po_pdf_bytes(db_path: str, requisition_id: int) -> bytes:
    """
    Generate purchase order PDF bytes for a requisition.

    Args:
        db_path: SQLite database path.
        requisition_id: Requisition ID.

    Returns:
        PDF file bytes.

    Raises:
        RuntimeError: If requisition not found or PDF generation fails.
    """
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req:
        raise RuntimeError("Requisition not found.")

    rows = list_requisitions_by_status(db_path, ["po_generated", "received", "billed", "approved"])
    enriched = next((r for r in rows if r["id"] == requisition_id), None)
    if enriched:
        req = {**req, **enriched}

    po_ref = req.get("po_reference") or ""
    return build_po_pdf(db_path, req, po_ref)


def build_report_pdf_bytes(
    db_path: str,
    rows: list,
    grand_total: float,
) -> bytes:
    """Build report PDF from filtered rows."""
    return generate_report_pdf(rows, grand_total)


def build_billed_summary_pdf_bytes(context: Dict[str, Any]) -> bytes:
    """Build billed PO summary PDF."""
    return generate_billed_summary_pdf(context)
