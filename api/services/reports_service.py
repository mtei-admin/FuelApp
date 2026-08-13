"""Reports aggregation and export service."""
import csv
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.database import list_requisitions_by_status, list_vendors, LEGACY_CC_VIA_PO_NOTE, SETTLEMENT_CREDIT_CARD, normalize_settlement_type

STATUS_GROUPS = {
    "Pending": ["pending"],
    "Approved": ["approved"],
    "PO Generated": ["po_generated"],
    "Released": ["released"],
    "Received": ["received"],
    "Billed": ["billed"],
    "Cancelled": ["cancelled"],
    "Paid (CC)": ["paid_cc"],
}


def _payment_label(row: Dict[str, Any]) -> str:
    """Human-readable payment path for exports (includes legacy CC via PO)."""
    settlement = normalize_settlement_type(row.get("settlement_type"))
    status = (row.get("status") or "").lower()
    notes = row.get("notes") or ""
    if settlement == SETTLEMENT_CREDIT_CARD:
        if status == "paid_cc":
            return "credit_card"
        if LEGACY_CC_VIA_PO_NOTE in notes or status in {
            "approved",
            "po_generated",
            "released",
            "received",
            "billed",
        }:
            return "credit_card (legacy PO)"
    return settlement


def _filter_by_date_range(
    data: List[Dict[str, Any]],
    from_date: Optional[date],
    to_date: Optional[date],
) -> List[Dict[str, Any]]:
    """Filter rows by created_at date inclusive."""
    if from_date is None and to_date is None:
        return data
    out: List[Dict[str, Any]] = []
    for row in data:
        raw = row.get("created_at") or ""
        if not raw:
            continue
        try:
            row_date = datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if from_date is not None and row_date < from_date:
            continue
        if to_date is not None and row_date > to_date:
            continue
        out.append(row)
    return out


NO_BILLING_REF_LABEL = "— No billing reference"


def _billing_ref_label(row: Dict[str, Any]) -> str:
    """Display label for vendor billing reference (invoice_number)."""
    ref = (row.get("invoice_number") or "").strip()
    return ref or NO_BILLING_REF_LABEL


def _group_billed_by_reference(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Nest billed rows by billing reference with count and total per reference.

    Empty references sort last under NO_BILLING_REF_LABEL.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in data:
        key = _billing_ref_label(row)
        buckets.setdefault(key, []).append(row)

    def sort_key(label: str) -> tuple:
        if label == NO_BILLING_REF_LABEL:
            return (1, "")
        return (0, label.upper())

    subgroups: List[Dict[str, Any]] = []
    for label in sorted(buckets.keys(), key=sort_key):
        rows = sorted(
            buckets[label],
            key=lambda x: str(x.get("po_reference") or x.get("serial_number") or ""),
        )
        subgroups.append(
            {
                "label": label,
                "invoice_number": None if label == NO_BILLING_REF_LABEL else label,
                "count": len(rows),
                "total": sum(float(row.get("total_price") or 0) for row in rows),
                "rows": rows,
            }
        )
    return subgroups


def build_report(
    db_path: str,
    plate_filter: str = "",
    vendor_filter: str = "",
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status_filter: str = "",
) -> Dict[str, Any]:
    """
    Build grouped report summary and flat rows for export.

    Args:
        db_path: SQLite database path.
        plate_filter: Optional partial plate match (case-insensitive).
        vendor_filter: Optional exact vendor name.
        from_date: Optional inclusive created_at start.
        to_date: Optional inclusive created_at end.
        status_filter: Optional status group label (e.g. "Received").
            Empty means all status groups.
    """
    plate_upper = plate_filter.strip().upper()
    vendor_selected = vendor_filter.strip()
    status_selected = status_filter.strip()
    groups: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []
    grand_total = 0.0

    status_items = STATUS_GROUPS.items()
    if status_selected:
        if status_selected not in STATUS_GROUPS:
            raise ValueError(
                f"Unknown status filter '{status_selected}'. "
                f"Use one of: {', '.join(STATUS_GROUPS.keys())}."
            )
        status_items = [(status_selected, STATUS_GROUPS[status_selected])]

    for label, statuses in status_items:
        data = list_requisitions_by_status(db_path, statuses)
        if plate_upper:
            data = [
                r for r in data
                if (r.get("plate_number") or "").upper().find(plate_upper) >= 0
            ]
        if vendor_selected:
            data = [
                r for r in data
                if (r.get("vendor_name") or "").strip() == vendor_selected
            ]
        data = _filter_by_date_range(data, from_date, to_date)

        subgroups: Optional[List[Dict[str, Any]]] = None
        if label == "Billed":
            subgroups = _group_billed_by_reference(data)
            data = [row for sub in subgroups for row in sub["rows"]]

        group_total = sum(float(row.get("total_price") or 0) for row in data)
        grand_total += group_total
        for row in data:
            all_rows.append({**row, "status_group": label})

        group_payload: Dict[str, Any] = {
            "label": label,
            "count": len(data),
            "total": group_total,
            "rows": data,
        }
        if subgroups is not None:
            group_payload["subgroups"] = subgroups
        groups.append(group_payload)

    return {
        "groups": groups,
        "rows": all_rows,
        "grand_total": grand_total,
        "vendors": list_vendors(db_path),
        "status_options": list(STATUS_GROUPS.keys()),
    }


def build_report_csv(rows: List[Dict[str, Any]]) -> bytes:
    """Build CSV bytes from report rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "PO No.", "Plate", "Quantity", "Unit", "Total Price", "Vendor",
        "Status", "Status Group", "Payment", "Invoice #", "CC Stmt #",
        "Requested By", "Created",
    ])
    for row in rows:
        qty = row.get("quantity") or ""
        unit = (row.get("unit") or "").strip() or "liters"
        if str(unit).upper() == "FULLTANK":
            qty = "Full Tank"
            unit = "FULLTANK"
        payment = _payment_label(row)
        writer.writerow([
            row.get("po_reference") or "",
            row.get("plate_number") or "",
            qty,
            unit,
            row.get("total_price") or "",
            row.get("vendor_name") or "",
            row.get("status") or "",
            row.get("status_group") or "",
            payment,
            row.get("invoice_number") or "",
            row.get("cc_statement_reference") or "",
            row.get("requester_name") or "",
            row.get("created_at") or "",
        ])
    return buffer.getvalue().encode("utf-8-sig")
