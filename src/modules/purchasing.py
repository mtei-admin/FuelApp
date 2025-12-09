"""Purchasing screen for generating purchase orders and marking receipt."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    list_requisitions_by_status,
    update_requisition_po,
    update_requisition_received,
)
from src.utils.pdf_gen import generate_purchase_order_pdf, render_purchase_order_html

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the purchasing UI.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() not in {"purchaser", "finance"}:
        st.error("You do not have permission to view purchasing.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Purchasing")
    st.caption("Generate POs for approved requests and mark receipts.")

    render_po_generation(path)
    st.divider()
    render_receiving(path)


def render_po_generation(db_path: str) -> None:
    """List approved requests and allow PO generation."""
    st.subheader("Approved Requests (Generate PO)")
    approved = safe_list_by_status(db_path, ["approved"])
    if not approved:
        st.info("No approved requests awaiting PO.")
        return

    for req in approved:
        cols = st.columns([3, 2, 2, 2, 2])
        cols[0].markdown(f"**{req['plate_number']}** — {req.get('vendor_name') or '—'}")
        cols[1].write(f"{req['quantity']} {req['unit']}")
        if req.get("total_price"):
            cols[2].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[2].write("—")
        cols[3].write(f"Requested by: {req.get('requester_name')}")
        po_ref = cols[4].text_input(
            "PO Ref (optional)",
            key=f"po_ref_{req['id']}",
            placeholder="PO-12345",
        )
        if cols[4].button("Generate PO & Download", key=f"po_btn_{req['id']}"):
            try:
                update_requisition_po(db_path, req["id"], po_ref.strip())
                pdf_bytes = build_po_pdf(req, po_ref.strip())
                st.download_button(
                    "Download PO PDF",
                    data=pdf_bytes,
                    file_name=f"PO_{po_ref.strip() or req['id']}.pdf",
                    mime="application/pdf",
                    key=f"po_dl_{req['id']}",
                )
                st.success("PO marked as generated.")
            except Exception as error:  # pragma: no cover - UI feedback
                st.error(str(error))


def render_receiving(db_path: str) -> None:
    """List PO-generated requests and allow marking as received."""
    st.subheader("PO Generated (Mark Received / Download)")
    po_generated = safe_list_by_status(db_path, ["po_generated"])
    if not po_generated:
        st.info("No PO-generated requests awaiting receipt.")
        return

    for req in po_generated:
        cols = st.columns([3, 2, 2, 3, 1, 2])
        cols[0].markdown(f"**{req['plate_number']}** — {req.get('vendor_name') or '—'}")
        cols[1].write(f"{req['quantity']} {req['unit']}")
        if req.get("total_price"):
            cols[2].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[2].write("—")
        cols[3].write(f"PO Ref: {req.get('po_reference') or '—'}")
        pdf_bytes = safe_build_po_pdf(req)
        if pdf_bytes:
            cols[4].download_button(
                "Download PO",
                data=pdf_bytes,
                file_name=f"PO_{req.get('po_reference') or req['id']}.pdf",
                mime="application/pdf",
                key=f"po_dl_generated_{req['id']}",
            )
        if cols[5].button("Mark Received", key=f"recv_btn_{req['id']}"):
            try:
                update_requisition_received(db_path, req["id"])
                st.success("Marked as received.")
                st.rerun()
            except Exception as error:  # pragma: no cover - UI feedback
                st.error(str(error))


def build_po_pdf(req: Dict[str, str], po_reference: str) -> bytes:
    """Build PO PDF bytes from requisition context."""
    unit_price = req.get("unit_price")
    total_price = req.get("total_price")
    context = {
        "po_reference": po_reference or req.get("po_reference"),
        "vendor_name": req.get("vendor_name"),
        "plate_number": req.get("plate_number"),
        "vehicle_model": req.get("model"),
        "requester_name": req.get("requester_name"),
        "status": req.get("status"),
        "created_at": req.get("created_at"),
        "quantity": req.get("quantity"),
        "unit": req.get("unit"),
        "unit_price": f"₱{unit_price:,.2f}" if unit_price else None,
        "total_price": f"₱{total_price:,.2f}" if total_price else None,
        "notes": req.get("notes"),
    }
    html = render_purchase_order_html(context)
    return generate_purchase_order_pdf(context | {"html": html})


def safe_build_po_pdf(req: Dict[str, str]) -> Optional[bytes]:
    """Safely generate PO PDF bytes; return None on error."""
    try:
        return build_po_pdf(req, req.get("po_reference", ""))
    except Exception as error:  # pragma: no cover - UI feedback
        st.warning(f"Could not generate PO PDF: {error}")
        return None


def safe_list_by_status(db_path: str, statuses: List[str]) -> List[dict]:
    """Safely list requisitions by status with UI feedback."""
    try:
        return list_requisitions_by_status(db_path, statuses)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requisitions: {error}")
        return []

