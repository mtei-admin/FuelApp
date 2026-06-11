"""Reporting screen for requisitions and purchasing data."""
import csv
import io
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import list_requisitions_by_status, list_vendors
from src.utils.pdf_gen import generate_report_pdf

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render a simple reporting view with optional search and report download.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() not in {"accounting", "superuser"}:
        st.error("You do not have permission to view reports.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Reports")
    st.caption("Summary of requisitions by status. Optionally filter and download.")

    # Optional search filters
    st.subheader("Search (optional)")
    vendors_from_master = _safe_list_vendors(path)
    vendor_names = sorted([v.get("name") or "" for v in vendors_from_master if v.get("name")])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        plate_filter = st.text_input(
            "Plate number",
            value="",
            placeholder="e.g. ABC-1234",
            key="reports_plate_filter",
            help="Leave empty to show all. Partial match, case-insensitive.",
        )
    with col2:
        vendor_filter = ""
        if vendor_names:
            options = ["(All vendors)"] + vendor_names
            selected = st.selectbox(
                "Select vendor",
                options=options,
                key="reports_vendor_select",
                help="From Vendor Master Data. Pick one or (All vendors).",
            )
            if selected and selected != "(All vendors)":
                vendor_filter = selected
        else:
            st.caption("No vendors in Master Data.")
    with col3:
        from_date = st.date_input(
            "From date",
            value=None,
            key="reports_from_date",
            help="Optional. Filter by request created date (start of day).",
        )
    with col4:
        to_date = st.date_input(
            "To date",
            value=None,
            key="reports_to_date",
            help="Optional. Filter by request created date (end of day).",
        )

    status_groups = {
        "Pending": ["pending"],
        "Approved": ["approved"],
        "PO Generated": ["po_generated"],
        "Received": ["received"],
        "Billed": ["billed"],
    }

    all_filtered_rows: List[Dict] = []
    total_cost = 0.0
    plate_upper = (plate_filter or "").strip().upper()
    vendor_selected = (vendor_filter or "").strip()

    for label, statuses in status_groups.items():
        data = safe_list_by_status(path, statuses)

        if plate_upper:
            data = [r for r in data if (r.get("plate_number") or "").upper().find(plate_upper) >= 0]
        if vendor_selected:
            data = [
                r for r in data
                if (r.get("vendor_name") or "").strip() == vendor_selected
            ]
        data = _filter_by_date_range(data, from_date, to_date)

        # Sort "Billed" group by invoice number (case-insensitive, None/empty at end)
        if label == "Billed":
            data = sorted(
                data,
                key=lambda x: (
                    (x.get("invoice_number") or "").strip().upper() or "ZZZZZZZZZZ"
                ),
            )

        for row in data:
            all_filtered_rows.append({**row, "status_group": label})

        group_total = sum(row.get("total_price") or 0.0 for row in data)
        total_cost += group_total

        with st.expander(f"{label} ({len(data)}) - Total: ₱{group_total:,.2f}", expanded=False):
            if not data:
                st.write("No records.")
                continue
            for row in data:
                serial_num = row.get("serial_number", "—")
                price_str = f" | ₱{row['total_price']:,.2f}" if row.get("total_price") else ""
                qty_text = (
                    "Full Tank"
                    if row.get("unit") and str(row.get("unit")).upper() == "FULLTANK"
                    else f"{row['quantity']} liters"
                )
                st.write(
                    f"- **{serial_num}** | {row['plate_number']} | {qty_text}{price_str} | "
                    f"{row.get('vendor_name') or '—'} | status: {row['status']} | "
                    f"PO: {row.get('po_reference') or '—'} | Invoice: {row.get('invoice_number') or '—'}"
                )

    st.divider()
    st.metric("Grand Total (All Statuses)", f"₱{total_cost:,.2f}")

    # Download report (CSV and PDF of filtered results)
    st.subheader("Download report")
    if all_filtered_rows:
        csv_bytes = _build_report_csv(all_filtered_rows)
        pdf_bytes = _build_report_pdf(all_filtered_rows, total_cost)
        c1, c2, _ = st.columns(3)
        with c1:
            st.download_button(
                "Download report (CSV)",
                data=csv_bytes,
                file_name="fuel_report.csv",
                mime="text/csv",
                key="reports_download_csv",
            )
        with c2:
            st.download_button(
                "Download report (PDF)",
                data=pdf_bytes,
                file_name="fuel_report.pdf",
                mime="application/pdf",
                key="reports_download_pdf",
            )
    else:
        st.info("No data to download. Adjust filters or ensure there are requisitions.")


def _build_report_csv(rows: List[Dict]) -> bytes:
    """Build a CSV file from report rows for download."""
    if not rows:
        return b""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Serial #",
        "Plate",
        "Quantity",
        "Unit",
        "Total Price",
        "Vendor",
        "Status",
        "Status Group",
        "PO Ref",
        "Invoice #",
        "Requested By",
        "Created",
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


def _filter_by_date_range(
    data: List[Dict],
    from_date: Optional[date],
    to_date: Optional[date],
) -> List[Dict]:
    """Filter rows by created_at within [from_date, to_date] (inclusive). None means no bound."""
    if from_date is None and to_date is None:
        return data
    out = []
    for row in data:
        raw = row.get("created_at") or ""
        if not raw:
            continue
        try:
            # created_at is "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
            row_date = datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if from_date is not None and row_date < from_date:
            continue
        if to_date is not None and row_date > to_date:
            continue
        out.append(row)
    return out


def _build_report_pdf(rows: List[Dict], grand_total: float) -> bytes:
    """Build a PDF report from filtered rows. Returns PDF bytes."""
    return generate_report_pdf(rows, grand_total)


def _safe_list_vendors(db_path: str) -> List[Dict]:
    """Return list of vendors from Master Data; empty list on error."""
    try:
        return list_vendors(db_path)
    except Exception:
        return []


def safe_list_by_status(db_path: str, statuses: List[str]) -> List[dict]:
    """Safely list requisitions by status with UI feedback."""
    try:
        return list_requisitions_by_status(db_path, statuses)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requisitions: {error}")
        return []

