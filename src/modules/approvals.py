"""Supervisor approval screen for fuel requisitions."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    list_pending_requisitions,
    update_requisition_status,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the approvals UI for supervisors to approve or reject requests.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    user_role = current_user.get("role", "").lower()
    if user_role not in {"supervisor", "purchaser", "finance"}:
        st.error("You do not have permission to view approvals.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Approvals")
    
    # Only supervisors and finance can approve/reject
    can_approve = user_role in {"supervisor", "finance"}
    if can_approve:
        st.caption("Review and decide on pending fuel requests.")
    else:
        st.caption("View pending fuel requests (read-only).")

    pending = safe_list_pending(path)
    if not pending:
        st.info("No pending requests.")
        return

    for req in pending:
        cols = st.columns([2, 2, 2, 2, 2, 2])
        cols[0].markdown(f"**{req['plate_number']}**")
        cols[1].write(f"{req['quantity']} {req['unit']}")
        cols[2].write(req.get("vendor_name") or "—")
        if req.get("total_price"):
            cols[3].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[3].write("—")
        cols[4].write(f"Requested by: {req.get('requester_name')}")
        
        # Only show approve/reject buttons for supervisors and finance
        if can_approve:
            approve = cols[5].button("Approve", key=f"approve_{req['id']}")
            reject = cols[5].button("Reject", key=f"reject_{req['id']}")
            if approve:
                update_status(path, req["id"], "approved", current_user["id"])
            if reject:
                update_status(path, req["id"], "rejected", current_user["id"])
        else:
            cols[5].write("View only")


def update_status(db_path: str, requisition_id: int, status: str, approver_id: int) -> None:
    """Update requisition status with UI feedback."""
    try:
        update_requisition_status(db_path, requisition_id, status, approver_id)
        st.success(f"Request {status}.")
        st.rerun()
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(str(error))


def safe_list_pending(db_path: str) -> List[dict]:
    """Safely list pending requisitions with error handling."""
    try:
        return list_pending_requisitions(db_path)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load pending requests: {error}")
        return []

