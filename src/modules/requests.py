"""Fuel request creation screen."""
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    create_requisition,
    list_cars,
    list_requisitions_for_user,
    list_vendors,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the fuel request submission UI.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Fuel Requests")
    st.caption("Submit new fuel requests and view your history.")

    render_request_form(path, current_user["id"])
    st.divider()
    render_history(path, current_user["id"])


def render_request_form(db_path: str, requester_id: int) -> None:
    """Render the form to create a new fuel requisition with auto-calc total."""
    # Initialize session state for duplicate prevention
    if "last_submission_hash" not in st.session_state:
        st.session_state.last_submission_hash = None
    
    cars = safe_list_cars(db_path)
    vendors = safe_list_vendors(db_path)
    car_map = {f"{c['plate_number']} - {c['model']}": c["id"] for c in cars}
    vendor_map = {v["name"]: v["id"] for v in vendors}

    with st.form("request_form", clear_on_submit=True):
        st.subheader("New Request")
        st.caption("💡 Tip: Use Tab or Enter to move between fields")
        
        vehicle_choice = st.selectbox(
            "Vehicle", list(car_map.keys()), key="req_vehicle", help="Required. Press Tab to move to next field."
        )
        vendor_choice = st.selectbox(
            "Vendor (optional)", ["(None)"] + list(vendor_map.keys()), key="req_vendor", help="Press Tab to move to next field."
        )
        quantity = st.number_input(
            "Quantity", min_value=0.0, step=1.0, key="req_quantity", help="Press Tab or Enter to move to next field."
        )
        unit = st.selectbox("Unit", ["liters", "gallons"], key="req_unit", help="Press Tab to move to next field.")
        unit_price = st.number_input(
            "Unit Price (optional)", 
            min_value=0.0, 
            step=0.01, 
            key="req_unit_price", 
            value=0.0,
            help="Press Tab or Enter to move to next field."
        )
        
        # Auto-calculate total
        total_price = quantity * unit_price if unit_price > 0 else None
        if total_price is not None:
            st.metric("Total Price", f"₱{total_price:,.2f}")
        
        notes = st.text_area(
            "Notes (optional)", 
            key="req_notes",
            help="Press Tab to move to submit button."
        )
        submitted = st.form_submit_button("Submit Request", use_container_width=True)

    if submitted:
        if not vehicle_choice or quantity <= 0:
            st.error("Vehicle and positive quantity are required.")
            return
        
        # Create a hash of the submission to prevent duplicates
        submission_data = f"{requester_id}_{vehicle_choice}_{vendor_choice}_{quantity}_{unit}_{unit_price}_{notes}"
        submission_hash = hashlib.md5(submission_data.encode()).hexdigest()
        
        # Check if this exact submission was already processed
        if st.session_state.last_submission_hash == submission_hash:
            st.warning("This request was already submitted. Please refresh the page if you want to submit a new request.")
            return
        
        vehicle_id = car_map.get(vehicle_choice)
        vendor_id = vendor_map.get(vendor_choice) if vendor_choice != "(None)" else None
        try:
            create_requisition(
                db_path=db_path,
                requester_id=requester_id,
                vehicle_id=vehicle_id,
                vendor_id=vendor_id,
                quantity=quantity,
                unit=unit,
                unit_price=unit_price if unit_price > 0 else None,
                notes=notes.strip(),
            )
            # Store the submission hash to prevent duplicates
            st.session_state.last_submission_hash = submission_hash
            st.success("Request submitted.")
            st.rerun()
        except Exception as error:  # pragma: no cover - user-facing
            st.error(str(error))


def render_history(db_path: str, requester_id: int) -> None:
    """Display the user's requisition history."""
    st.subheader("My Requests")
    requests = safe_list_user_requisitions(db_path, requester_id)
    if not requests:
        st.info("No requests yet.")
        return

    for req in requests:
        cols = st.columns([2, 2, 2, 2, 2, 1])
        cols[0].markdown(f"**{req['plate_number']}**")
        cols[1].write(f"{req['quantity']} {req['unit']}")
        cols[2].write(req.get("vendor_name") or "—")
        if req.get("total_price"):
            cols[3].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[3].write("—")
        cols[4].write(req["status"].title())
        cols[5].write(req["created_at"])
        if req.get("notes"):
            st.caption(req["notes"])


def safe_list_cars(db_path: str) -> List[dict]:
    """Safely list cars with error handling."""
    try:
        return list_cars(db_path)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load cars: {error}")
        return []


def safe_list_vendors(db_path: str) -> List[dict]:
    """Safely list vendors with error handling."""
    try:
        return list_vendors(db_path)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load vendors: {error}")
        return []


def safe_list_user_requisitions(db_path: str, requester_id: int) -> List[dict]:
    """Safely list requisitions for a user with error handling."""
    try:
        return list_requisitions_for_user(db_path, requester_id)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requests: {error}")
        return []

