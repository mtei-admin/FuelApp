"""Billing reconciliation screen for finance."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import list_requisitions_by_status, update_requisition_billed

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the billing UI for reconciling vendor invoices with received POs.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() not in {"finance"}:
        st.error("You do not have permission to view billing.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Billing")
    st.caption("Match received POs with vendor invoices using batch selection.")

    received = safe_list_by_status(path, ["received"])
    if not received:
        st.info("No received items awaiting billing.")
        return

    # Batch billing section with checkboxes
    st.subheader("Select Items to Bill")
    invoice_number = st.text_input("Vendor Invoice #", placeholder="INV-12345", key="batch_invoice")
    
    selected_ids = []
    for req in received:
        price_str = f" | ₱{req['total_price']:,.2f}" if req.get("total_price") else ""
        checkbox_key = f"bill_check_{req['id']}"
        if st.checkbox(
            f"{req['plate_number']} — {req.get('vendor_name') or '—'} | "
            f"{req['quantity']} {req['unit']}{price_str} | PO: {req.get('po_reference') or '—'}",
            key=checkbox_key,
        ):
            selected_ids.append(req["id"])

    if selected_ids:
        st.write(f"**{len(selected_ids)} item(s) selected**")
        if st.button("Mark Selected as Billed", type="primary"):
            if not invoice_number.strip():
                st.error("Invoice number is required.")
            else:
                try:
                    for req_id in selected_ids:
                        update_requisition_billed(path, req_id, invoice_number.strip())
                    st.success(f"Marked {len(selected_ids)} item(s) as billed with invoice {invoice_number}.")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))


def safe_list_by_status(db_path: str, statuses: List[str]) -> List[dict]:
    """Safely list requisitions by status with UI feedback."""
    try:
        return list_requisitions_by_status(db_path, statuses)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requisitions: {error}")
        return []

