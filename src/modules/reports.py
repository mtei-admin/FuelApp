"""Reporting screen for requisitions and purchasing data."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import list_requisitions_by_status

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render a simple reporting view.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() not in {"finance"}:
        st.error("You do not have permission to view reports.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Reports")
    st.caption("Summary of requisitions by status.")

    status_groups = {
        "Pending": ["pending"],
        "Approved": ["approved"],
        "PO Generated": ["po_generated"],
        "Received": ["received"],
        "Billed": ["billed"],
    }

    total_cost = 0.0
    for label, statuses in status_groups.items():
        data = safe_list_by_status(path, statuses)
        group_total = sum(row.get("total_price") or 0.0 for row in data)
        total_cost += group_total
        
        with st.expander(f"{label} ({len(data)}) - Total: ₱{group_total:,.2f}", expanded=False):
            if not data:
                st.write("No records.")
                continue
            for row in data:
                price_str = f" | ₱{row['total_price']:,.2f}" if row.get("total_price") else ""
                st.write(
                    f"- {row['plate_number']} | {row['quantity']} {row['unit']}{price_str} | "
                    f"{row.get('vendor_name') or '—'} | status: {row['status']} | "
                    f"PO: {row.get('po_reference') or '—'} | Invoice: {row.get('invoice_number') or '—'}"
                )
    
    st.divider()
    st.metric("Grand Total (All Statuses)", f"₱{total_cost:,.2f}")


def safe_list_by_status(db_path: str, statuses: List[str]) -> List[dict]:
    """Safely list requisitions by status with UI feedback."""
    try:
        return list_requisitions_by_status(db_path, statuses)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requisitions: {error}")
        return []

