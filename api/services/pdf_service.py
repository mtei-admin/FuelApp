"""PDF / Excel generation helpers for API document downloads."""
from typing import Any, Dict, Optional

from src.modules.purchasing import build_po_pdf
from src.database import fetch_requisition_by_id, list_requisitions_by_status
from src.utils.pdf_gen import (
    generate_billed_summary_pdf,
    generate_cc_reconcile_summary_pdf,
    generate_report_pdf,
)
from src.utils.xlsx_gen import (
    generate_billed_summary_xlsx,
    generate_cc_reconcile_summary_xlsx,
    safe_export_filename_part,
)


def build_po_pdf_bytes(db_path: str, requisition_id: int, downloader_name: str = "") -> bytes:
    """
    Generate purchase order PDF bytes for a requisition.

    Args:
        db_path: SQLite database path.
        requisition_id: Requisition ID.
        downloader_name: Full name of the user downloading the PDF.

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
    return build_po_pdf(db_path, req, po_ref, downloader_name=downloader_name)


def build_report_pdf_bytes(
    db_path: str,
    rows: list,
    grand_total: float,
    groups: Optional[list] = None,
) -> bytes:
    """Build report PDF from filtered rows (optional nested status/billing groups)."""
    return generate_report_pdf(rows, grand_total, groups=groups)


def build_billed_summary_pdf_bytes(context: Dict[str, Any]) -> bytes:
    """Build billed PO summary PDF."""
    return generate_billed_summary_pdf(context)


def build_billed_summary_xlsx_bytes(context: Dict[str, Any]) -> bytes:
    """Build billed PO summary Excel (.xlsx) workbook."""
    return generate_billed_summary_xlsx(context)


def build_cc_reconcile_summary_pdf_bytes(context: Dict[str, Any]) -> bytes:
    """Build CC reconciliation summary PDF."""
    return generate_cc_reconcile_summary_pdf(context)


def build_cc_reconcile_summary_xlsx_bytes(context: Dict[str, Any]) -> bytes:
    """Build CC reconciliation summary Excel (.xlsx) workbook."""
    return generate_cc_reconcile_summary_xlsx(context)


def billed_summary_download_stem(invoice_number: str) -> str:
    """Filename stem for billed summary downloads."""
    return safe_export_filename_part(invoice_number, fallback="batch")


def cc_reconcile_download_stem(report_number: str) -> str:
    """Filename stem for CC reconciliation summary downloads."""
    return safe_export_filename_part(report_number, fallback="batch")
