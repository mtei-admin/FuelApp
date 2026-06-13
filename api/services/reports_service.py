"""Reports aggregation and export service."""
import csv
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.database import list_requisitions_by_status, list_vendors

STATUS_GROUPS = {
    "Pending": ["pending"],
    "Approved": ["approved"],
    "PO Generated": ["po_generated"],
    "Received": ["received"],
    "Billed": ["billed"],
}


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


def build_report(
    db_path: str,
    plate_filter: str = "",
    vendor_filter: str = "",
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Build grouped report summary and flat rows for export."""
    plate_upper = plate_filter.strip().upper()
    vendor_selected = vendor_filter.strip()
    groups: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []
    grand_total = 0.0

    for label, statuses in STATUS_GROUPS.items():
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

        if label == "Billed":
            data = sorted(
                data,
                key=lambda x: (
                    (x.get("invoice_number") or "").strip().upper() or "ZZZZZZZZZZ"
                ),
            )

        group_total = sum(float(row.get("total_price") or 0) for row in data)
        grand_total += group_total
        for row in data:
            all_rows.append({**row, "status_group": label})

        groups.append({
            "label": label,
            "count": len(data),
            "total": group_total,
            "rows": data,
        })

    return {
        "groups": groups,
        "rows": all_rows,
        "grand_total": grand_total,
        "vendors": list_vendors(db_path),
    }


def build_report_csv(rows: List[Dict[str, Any]]) -> bytes:
    """Build CSV bytes from report rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Serial #", "Plate", "Quantity", "Unit", "Total Price", "Vendor",
        "Status", "Status Group", "PO Ref", "Invoice #", "Requested By", "Created",
    ])
    for row in rows:
        qty = row.get("quantity") or ""
        unit = (row.get("unit") or "").strip() or "liters"
        if str(unit).upper() == "FULLTANK":
            qty = "Full Tank"
            unit = "FULLTANK"
        writer.writerow([
            row.get("serial_number") or "",
            row.get("plate_number") or "",
            qty,
            unit,
            row.get("total_price") or "",
            row.get("vendor_name") or "",
            row.get("status") or "",
            row.get("status_group") or "",
            row.get("po_reference") or "",
            row.get("invoice_number") or "",
            row.get("requester_name") or "",
            row.get("created_at") or "",
        ])
    return buffer.getvalue().encode("utf-8-sig")
