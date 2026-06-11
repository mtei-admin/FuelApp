"""Approver approval screen for fuel requisitions."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

from src.database import (
    fetch_requisition_by_id,
    get_vendor_fuel_price_for_fuel_type,
    list_pending_requisitions,
    update_requisition,
    update_requisition_status,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the approvals UI for approvers to approve or reject requests.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    user_role = current_user.get("role", "").lower()
    if user_role not in {"approver", "purchaser", "accounting", "superuser"}:
        st.error("You do not have permission to view approvals.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Approvals")

    # Decide layout mode (desktop vs mobile) based on URL param and browser width.
    layout_mode = _get_approvals_layout_mode()

    # Only approvers, accounting, and superuser can approve/reject
    can_approve = user_role in {"approver", "accounting", "superuser"}
    if can_approve:
        st.caption("Review and decide on pending fuel requests.")
    else:
        st.caption("View pending fuel requests (read-only).")

    pending = safe_list_pending(path)
    if not pending:
        st.info("No pending requests.")
        return

    if layout_mode == "mobile":
        _render_mobile_approvals(pending, path, current_user, can_approve)
    else:
        _render_desktop_approvals(pending, path, current_user, can_approve)


def _get_approvals_layout_mode() -> str:
    """
    Determine approvals layout mode ('desktop' or 'mobile').

    Uses URL parameter 'approvals_layout':
    - If set to 'mobile' or 'desktop', respects that.
    - If missing or 'auto', injects a small JS snippet that sets it
      based on browser width on first load, then falls back to desktop.
    """
    try:
        raw_values = st.query_params.get("approvals_layout") or ["auto"]
    except Exception:  # pragma: no cover - defensive fallback
        raw_values = ["auto"]
    raw = (raw_values[0] or "auto").lower()
    if raw not in {"auto", "desktop", "mobile"}:
        raw = "auto"

    _inject_layout_detection_script()

    if raw == "mobile":
        return "mobile"
    if raw == "desktop":
        return "desktop"
    # Default for 'auto' before JS updates URL
    return "desktop"


def _inject_layout_detection_script() -> None:
    """
    Inject a tiny JS snippet that inspects browser width once and
    sets ?approvals_layout=mobile/desktop in the top-level URL.

    This allows automatic mobile layout on phones/tablets while still
    keeping all logic in Python.
    """
    components.html(
        """
        <script>
        (function() {
          try {
            var w = window.parent || window;
            if (!w || !w.location) {
              return;
            }
            var params = new URLSearchParams(w.location.search || "");
            var current = (params.get("approvals_layout") || "auto").toLowerCase();
            if (current !== "auto") {
              return;
            }
            var width = w.innerWidth || w.document.documentElement.clientWidth || w.document.body.clientWidth;
            var target = width <= 800 ? "mobile" : "desktop";
            if (target === current) {
              return;
            }
            params.set("approvals_layout", target);
            var newUrl = w.location.pathname + "?" + params.toString();
            w.history.replaceState(null, "", newUrl);
            w.location.reload();
          } catch (e) {
            console && console.log && console.log("approvals layout detection error", e);
          }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _render_desktop_approvals(
    pending: List[Dict[str, object]],
    path: str,
    current_user: Dict[str, str],
    can_approve: bool,
) -> None:
    """Render the existing desktop/table approvals layout."""
    # Header row
    header_cols = st.columns([1.5, 2, 2, 2, 2, 2, 2])
    header_cols[0].markdown("**Serial #**")
    header_cols[1].markdown("**Vehicle**")
    header_cols[2].markdown("**Quantity**")
    header_cols[3].markdown("**Vendor**")
    header_cols[4].markdown("**Total Price**")
    header_cols[5].markdown("**Requested By**")
    header_cols[6].markdown("**Action**")
    st.divider()

    for req in pending:
        cols = st.columns([1.5, 2, 2, 2, 2, 2, 2])
        cols[0].markdown(f"**{req.get('serial_number', '—')}**")
        vehicle_display = f"{req['plate_number']} - {req.get('model') or '—'}"
        cols[1].markdown(f"**{vehicle_display}**")
        qty_text = (
            "Full Tank"
            if req.get("unit") and str(req.get("unit")).upper() == "FULLTANK"
            else f"{req['quantity']} liters"
        )
        cols[2].write(qty_text)
        cols[3].write(req.get("vendor_name") or "—")
        # Show total price using latest vendor fuel price (pending requests don't have PO price yet)
        display_total = _approval_display_total(path, req)
        if display_total is not None:
            cols[4].write(f"₱{display_total:,.2f}")
        else:
            cols[4].write("—")
        cols[5].write(req.get("requester_name") or "—")

        # Only show edit/approve/reject buttons for approvers, accounting, and superuser
        if can_approve:
            # Create 3 sub-columns within the action column for side-by-side buttons
            action_col = cols[6]
            btn_col1, btn_col2, btn_col3 = action_col.columns(3)

            edit = btn_col1.button("✏️", key=f"edit_{req['id']}", use_container_width=True)
            approve = btn_col2.button("✓", key=f"approve_{req['id']}", use_container_width=True)
            reject = btn_col3.button("❌", key=f"reject_{req['id']}", use_container_width=True)

            if edit:
                # Store edit data in session state
                st.session_state.editing_approval = {
                    "req_id": req["id"],
                    "path": path,
                    "current_user": current_user,
                }
                st.rerun()

            if approve:
                # Store approval data in session state for dialog
                st.session_state.pending_approval = {
                    "req": req,
                    "path": path,
                    "user_id": current_user["id"],
                    "action": "approved",
                }
                # Trigger dialog
                show_approve_confirmation()

            if reject:
                # Store rejection data in session state for dialog
                st.session_state.pending_approval = {
                    "req": req,
                    "path": path,
                    "user_id": current_user["id"],
                    "action": "rejected",
                }
                # Trigger dialog
                show_reject_confirmation()
        else:
            cols[6].write("View only")

        # Show edit form if this request is being edited
        if can_approve and st.session_state.get("editing_approval", {}).get("req_id") == req["id"]:
            st.divider()
            render_edit_quantity_form(path, req["id"], current_user)
            st.divider()


def _render_mobile_approvals(
    pending: List[Dict[str, object]],
    path: str,
    current_user: Dict[str, str],
    can_approve: bool,
) -> None:
    """Render a mobile-friendly approvals layout (card per request)."""
    st.caption("Mobile layout: one request per card for easier tapping.")

    for req in pending:
        with st.container():
            st.markdown(f"**Serial #:** {req.get('serial_number', '—')}")
            vehicle_display = f"{req['plate_number']} - {req.get('model') or '—'}"
            st.markdown(f"**Vehicle:** {vehicle_display}")
            st.markdown(f"**Vendor:** {req.get('vendor_name') or '—'}")
            qty_text = (
                "Full Tank"
                if req.get("unit") and str(req.get("unit")).upper() == "FULLTANK"
                else f"{req['quantity']} liters"
            )
            st.markdown(f"**Quantity:** {qty_text}")
            display_total = _approval_display_total(path, req)
            if display_total is not None:
                st.markdown(f"**Total Price:** ₱{display_total:,.2f}")
            else:
                st.markdown("**Total Price:** —")
            st.markdown(f"**Requested By:** {req.get('requester_name') or '—'}")

            if can_approve:
                col1, col2, col3 = st.columns(3)
                edit = col1.button(
                    "Edit",
                    key=f"m_edit_{req['id']}",
                    use_container_width=True,
                )
                approve = col2.button(
                    "Approve",
                    key=f"m_approve_{req['id']}",
                    use_container_width=True,
                )
                reject = col3.button(
                    "Reject",
                    key=f"m_reject_{req['id']}",
                    use_container_width=True,
                )

                if edit:
                    st.session_state.editing_approval = {
                        "req_id": req["id"],
                        "path": path,
                        "current_user": current_user,
                    }
                    st.rerun()

                if approve:
                    st.session_state.pending_approval = {
                        "req": req,
                        "path": path,
                        "user_id": current_user["id"],
                        "action": "approved",
                    }
                    show_approve_confirmation()

                if reject:
                    st.session_state.pending_approval = {
                        "req": req,
                        "path": path,
                        "user_id": current_user["id"],
                        "action": "rejected",
                    }
                    show_reject_confirmation()
            else:
                st.info("View only")

            # Show edit form if this request is being edited
            if can_approve and st.session_state.get("editing_approval", {}).get("req_id") == req["id"]:
                st.divider()
                render_edit_quantity_form(path, req["id"], current_user)
        st.divider()


@st.dialog("Confirm Approval")
def show_approve_confirmation():
    """Show confirmation dialog for approval."""
    if "pending_approval" not in st.session_state:
        st.error("No pending approval found.")
        return
    
    pending = st.session_state.pending_approval
    req = pending["req"]
    
    qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
    
    st.write("**Please review the request details:**")
    st.write(f"**Serial #:** {req.get('serial_number', '—')}")
    st.write(f"**Vehicle:** {req['plate_number']}")
    st.write(f"**Vendor:** {req.get('vendor_name') or '—'}")
    st.write(f"**Quantity:** {qty_text}")
    st.write(f"**Requested By:** {req.get('requester_name') or '—'}")
    st.write("")
    st.write("Are you sure you want to **approve** this request?")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Approve", use_container_width=True, key=f"confirm_approve_{req['id']}"):
        update_status(pending["path"], req["id"], "approved", pending["user_id"])
        # Clear pending approval
        del st.session_state.pending_approval
    
    if col2.button("Cancel", use_container_width=True, key=f"cancel_approve_{req['id']}"):
        # Clear pending approval
        if "pending_approval" in st.session_state:
            del st.session_state.pending_approval
        st.rerun()


@st.dialog("Confirm Rejection")
def show_reject_confirmation():
    """Show confirmation dialog for rejection."""
    if "pending_approval" not in st.session_state:
        st.error("No pending approval found.")
        return
    
    pending = st.session_state.pending_approval
    req = pending["req"]
    
    qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
    
    st.write("**Please review the request details:**")
    st.write(f"**Serial #:** {req.get('serial_number', '—')}")
    st.write(f"**Vehicle:** {req['plate_number']}")
    st.write(f"**Vendor:** {req.get('vendor_name') or '—'}")
    st.write(f"**Quantity:** {qty_text}")
    st.write(f"**Requested By:** {req.get('requester_name') or '—'}")
    st.write("")
    st.warning("Are you sure you want to **reject** this request?")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Reject", use_container_width=True, key=f"confirm_reject_{req['id']}"):
        update_status(pending["path"], req["id"], "rejected", pending["user_id"])
        # Clear pending approval
        del st.session_state.pending_approval
    
    if col2.button("Cancel", use_container_width=True, key=f"cancel_reject_{req['id']}"):
        # Clear pending approval
        if "pending_approval" in st.session_state:
            del st.session_state.pending_approval
        st.rerun()


def update_status(db_path: str, requisition_id: int, status: str, approver_id: int) -> None:
    """Update requisition status with UI feedback."""
    try:
        update_requisition_status(db_path, requisition_id, status, approver_id)
        st.success(f"Request {status}.")
        st.rerun()
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(str(error))


def _approval_display_total(db_path: str, req: Dict[str, object]) -> Optional[float]:
    """
    Compute total price for display on Approvals using latest vendor fuel price.

    Returns quantity × unit_price when we have a numeric quantity and a current
    unit price for the request's vendor and fuel type; None for FULLTANK or no price.
    """
    if req.get("unit") and str(req.get("unit")).upper() == "FULLTANK":
        return None
    try:
        qty = float(req.get("quantity") or 0)
    except (TypeError, ValueError):
        return None
    if qty <= 0:
        return None
    unit_price = get_vendor_fuel_price_for_fuel_type(
        db_path, req.get("vendor_id"), req.get("fuel_type")
    )
    if unit_price is None or unit_price <= 0:
        return None
    return qty * unit_price


def safe_list_pending(db_path: str) -> List[dict]:
    """Safely list pending requisitions with error handling."""
    try:
        return list_pending_requisitions(db_path)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load pending requests: {error}")
        return []


def render_edit_quantity_form(
    db_path: str, requisition_id: int, current_user: Dict[str, str]
) -> None:
    """
    Render the edit quantity form for approvers.

    This allows approvers/accounting to adjust the requested quantity before
    approval. The actual dispensed quantity for FULLTANK requests is still
    captured later in the Billing module.

    Args:
        db_path: Database path.
        requisition_id: ID of the requisition to edit.
        current_user: Dict with user context (id, username, role).
    """
    # Fetch full requisition details
    full_req = fetch_requisition_by_id(db_path, requisition_id)
    if not full_req:
        st.error("Requisition not found.")
        return

    st.subheader(f"Edit Quantity - Serial # {full_req.get('serial_number', '—')}")
    st.caption("You can modify the requested quantity before approving this request.")

    # Display read-only fields
    st.write(f"**Vehicle:** {full_req['plate_number']} - {full_req.get('model', '')}")
    st.write(f"**Vendor:** {full_req.get('vendor_name') or '—'}")
    st.divider()

    # Quantity mode (Numeric vs FULLTANK)
    initial_mode = "FULLTANK" if full_req.get("unit", "").upper() == "FULLTANK" else "Numeric"
    mode_key = f"approval_qty_mode_{requisition_id}"
    if mode_key not in st.session_state:
        st.session_state[mode_key] = initial_mode

    qty_mode = st.radio(
        "Quantity Type",
        options=["Numeric", "FULLTANK"],
        index=0 if st.session_state[mode_key] != "FULLTANK" else 1,
        key=mode_key,
        horizontal=True,
        help=(
            "Choose Numeric to enter liters or FULLTANK for a full tank request. "
            "Actual refilled quantity for FULLTANK will still be captured during Billing."
        ),
    )

    if initial_mode == "FULLTANK" and qty_mode == "Numeric":
        st.info("You've switched from FULLTANK to Numeric. Please enter the quantity in liters below.")

    with st.form(f"edit_quantity_form_{requisition_id}", clear_on_submit=False):
        # Determine starting quantity value
        if qty_mode == "Numeric":
            if initial_mode == "Numeric":
                current_quantity = float(full_req.get("quantity", 0))
            else:
                current_quantity = float(full_req.get("quantity", 0)) or 1.0
        else:
            current_quantity = 0.0

        quantity = st.number_input(
            "Quantity (liters)",
            min_value=0.0,
            step=1.0,
            value=current_quantity,
            disabled=(qty_mode == "FULLTANK"),
            key=f"approval_quantity_{requisition_id}",
            help="Enter the quantity in liters. Disabled for FULLTANK requests.",
        )

        # Notes (optional)
        notes = st.text_area(
            "Notes (optional)",
            value=full_req.get("notes") or "",
            key=f"approval_notes_{requisition_id}",
            help="Optional notes about this edit.",
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

    if cancelled:
        if "editing_approval" in st.session_state:
            del st.session_state.editing_approval
        st.rerun()

    if submitted:
        # Validate numeric quantity
        if qty_mode == "Numeric":
            if quantity is None or quantity <= 0:
                st.error("Positive quantity is required for numeric mode.")
                return
        else:
            quantity = 0.0

        # Get vehicle and vendor IDs
        vehicle_id = full_req.get("vehicle_id")
        vendor_id = full_req.get("vendor_id")

        try:
            update_requisition(
                db_path=db_path,
                requisition_id=requisition_id,
                user_id=current_user["id"],
                user_role=current_user["role"],
                vehicle_id=vehicle_id,
                vendor_id=vendor_id,
                quantity=quantity,
                unit="FULLTANK" if qty_mode == "FULLTANK" else "liters",
                unit_price=full_req.get("unit_price"),
                notes=notes.strip(),
                fuel_type=full_req.get("fuel_type"),
            )
            if "editing_approval" in st.session_state:
                del st.session_state.editing_approval
            st.success("Quantity updated successfully.")
            st.rerun()
        except Exception as error:  # pragma: no cover - user-facing
            st.error(str(error))

