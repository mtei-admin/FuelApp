"""Billing reconciliation screen for accounting (and purchaser viewing)."""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    list_requisitions_by_status,
    update_requisition_billed,
    update_requisition_actual_quantity,
)
from src.utils.pdf_gen import generate_billed_summary_pdf

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
    if current_user.get("role", "").lower() not in {"purchaser", "accounting", "superuser"}:
        st.error("You do not have permission to view billing.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Billing")
    st.caption("Match received POs with vendor invoices using batch selection.")

    # Show short-lived success message from a previous Update (set before rerun)
    _key = "billing_update_success"
    if _key in st.session_state:
        st.success(st.session_state.pop(_key, None))

    # If there is a recently billed batch, offer a summary download
    batch_key = "billing_last_billed_batch"
    last_batch = st.session_state.get(batch_key)
    if last_batch:
        st.subheader("Billed PO Summary")
        try:
            pdf_bytes = generate_billed_summary_pdf(last_batch)
            file_name = f"Billed_PO_Summary_{last_batch.get('invoice_number') or 'no_invoice'}.pdf"
            st.download_button(
                "Download Billed Summary (PDF)",
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
                key="download_billed_summary",
            )
        except Exception as error:  # pragma: no cover - UI feedback
            st.error(f"Unable to generate billed summary PDF: {error}")

        if st.button("Clear Billed Summary", key="clear_billed_summary"):
            del st.session_state[batch_key]
            st.rerun()

    received = safe_list_by_status(path, ["received"])
    if not received:
        st.info("No received items awaiting billing.")
        return

    # Batch billing section with checkboxes
    st.subheader("Select Items to Bill")
    invoice_number = st.text_input("Vendor Invoice # (optional)", placeholder="INV-12345", key="batch_invoice")
    
    selected_ids = []
    for req in received:
        serial_num = req.get('serial_number', '—')
        is_fulltank = req.get("unit") and req.get("unit").upper() == "FULLTANK"
        
        # For FULLTANK items, show actual_quantity input field
        if is_fulltank:
            # Get current actual_quantity or default to 0
            current_actual_qty = req.get("actual_quantity") or 0.0
            actual_qty_key = f"actual_qty_{req['id']}"
            update_btn_key = f"update_qty_{req['id']}"
            
            # Create columns for layout: checkbox | details | actual_qty input | update button
            col1, col2, col3, col4 = st.columns([0.5, 3, 1.2, 0.8])
            
            with col2:
                # Display basic info
                qty_display = f"Full Tank ({current_actual_qty} liters)" if current_actual_qty > 0 else "Full Tank"
                price_display = f" | ₱{req['total_price']:,.2f}" if req.get("total_price") else ""
                st.write(
                    f"**{serial_num}** | {req['plate_number']} — {req.get('vendor_name') or '—'} | "
                    f"{qty_display}{price_display} | PO: {req.get('po_reference') or '—'}"
                )
            
            with col3:
                # Actual quantity input field
                actual_qty = st.number_input(
                    "Actual Qty (liters)",
                    min_value=0.0,
                    value=current_actual_qty,
                    step=0.1,
                    key=actual_qty_key,
                    help="Enter the actual quantity refilled",
                    label_visibility="visible"
                )
            
            with col4:
                # Update button
                if st.button("Update", key=update_btn_key, use_container_width=True):
                    if actual_qty > 0:
                        try:
                            update_requisition_actual_quantity(path, req["id"], actual_qty)
                            st.session_state["billing_update_success"] = f"Updated: {actual_qty} liters"
                            st.rerun()
                        except Exception as error:
                            st.error(f"Error: {error}")
                    else:
                        st.error("Please enter a quantity greater than 0")
            
            # Checkbox only when actual_quantity is committed (i.e. after Update was pressed)
            with col1:
                if current_actual_qty > 0:
                    checkbox_key = f"bill_check_{req['id']}"
                    if st.checkbox("", key=checkbox_key):
                        selected_ids.append(req["id"])
                else:
                    st.write("")  # Empty space to align with other rows
        else:
            # For numeric quantities, show normal checkbox
            serial_num = req.get('serial_number', '—')
            price_str = f" | ₱{req['total_price']:,.2f}" if req.get("total_price") else ""
            qty_text = f"{req['quantity']} liters"
            
            checkbox_key = f"bill_check_{req['id']}"
            if st.checkbox(
                f"**{serial_num}** | {req['plate_number']} — {req.get('vendor_name') or '—'} | "
                f"{qty_text}{price_str} | PO: {req.get('po_reference') or '—'}", 
                key=checkbox_key,
            ):
                selected_ids.append(req["id"])

    if selected_ids:
        st.write(f"**{len(selected_ids)} item(s) selected**")
        if st.button("Mark Selected as Billed", type="primary"):
            try:
                invoice_num = invoice_number.strip() if invoice_number else ""
                # Persist summary context for the just-billed batch
                billed_items = [req for req in received if req["id"] in selected_ids]
                st.session_state["billing_last_billed_batch"] = {
                    "invoice_number": invoice_num,
                    "billing_date": datetime.now().strftime("%Y-%m-%d"),
                    "items": billed_items,
                }

                for req_id in selected_ids:
                    update_requisition_billed(path, req_id, invoice_num)

                if invoice_num:
                    st.success(f"Marked {len(selected_ids)} item(s) as billed with invoice {invoice_num}.")
                else:
                    st.success(f"Marked {len(selected_ids)} item(s) as billed.")
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

