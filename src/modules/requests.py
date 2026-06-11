"""Fuel request creation screen."""
import base64
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    can_user_edit_requisition,
    check_prior_approved_requests,
    create_requisition,
    fetch_full_name_by_id,
    fetch_requisition_by_id,
    list_cars,
    list_requisitions_for_user,
    list_vendors,
    update_requisition,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def get_company_logo_paths(company: Optional[str]) -> List[Optional[str]]:
    """
    Get the logo file path(s) based on company name.
    Returns a list to support dual logos for certain companies.
    
    Args:
        company: Company name (MTEI, DSRDC, DIC, GCEIC, MTEI Trucking, or None).
    
    Returns:
        List of absolute paths to logo files. Empty list if no logos found.
        - MTEI: [DDD_logo.png, mte_logo.png]
        - DIC: [eskina_logo.png, dic_logo.png]
        - Others: Single logo in list
    """
    if not company:
        # Default to MTE logo for vehicles without company
        company = "MTEI"
    
    logo_paths = []
    assets_dir = Path("assets")
    
    if company == "MTEI":
        # MTEI gets dual logos: DDD_logo then mte_logo
        ddd_logo = assets_dir / "DDD_logo.png"
        mte_logo = assets_dir / "mte_logo.png"
        if ddd_logo.exists():
            logo_paths.append(str(ddd_logo.resolve()))
        if mte_logo.exists():
            logo_paths.append(str(mte_logo.resolve()))
    elif company == "DIC":
        # DIC gets dual logos: eskina_logo then dic_logo
        eskina_logo = assets_dir / "eskina_logo.png"
        dic_logo = assets_dir / "dic_logo.png"
        if eskina_logo.exists():
            logo_paths.append(str(eskina_logo.resolve()))
        if dic_logo.exists():
            logo_paths.append(str(dic_logo.resolve()))
    else:
        # Single logo for other companies
        logo_map = {
            "DSRDC": "DSRDC_logo.png",
            "GCEIC": "mte_logo.png",
            "MTEI Trucking": "mte_logo.png",
        }
        logo_filename = logo_map.get(company, "mte_logo.png")  # Default to MTE logo
        logo_path = assets_dir / logo_filename
        if logo_path.exists():
            logo_paths.append(str(logo_path.resolve()))
        else:
            # Fallback to MTE logo if company-specific logo doesn't exist
            fallback_path = assets_dir / "mte_logo.png"
            if fallback_path.exists():
                logo_paths.append(str(fallback_path.resolve()))
    
    return logo_paths


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
    
    # Get selected vehicle to determine company logo(s)
    selected_vehicle = st.session_state.get("req_vehicle", "")
    company_logo_paths = []
    
    if selected_vehicle:
        # Load cars to get company info
        try:
            cars = list_cars(path)
            car_map = {f"{c['plate_number']} - {c['model']}": c for c in cars}
            selected_car = car_map.get(selected_vehicle)
            if selected_car:
                company = selected_car.get("company")
                company_logo_paths = get_company_logo_paths(company)
        except Exception:
            # Silently fail - don't block page if logo lookup fails
            pass
    
    # Adjust column ratio based on number of logos (dual logos need more space)
    num_logos = len(company_logo_paths)
    if num_logos > 1:
        # Dual logos: give more space to logo column
        title_col, logo_col = st.columns([2.5, 1.5])
    else:
        # Single logo: original ratio
        title_col, logo_col = st.columns([3, 1])
    
    with title_col:
        st.title("Fuel Requests")
        st.caption("Submit new fuel requests and view your history.")
    
    with logo_col:
        if company_logo_paths:
            if len(company_logo_paths) > 1:
                # Dual logos: display side-by-side with centered horizontal alignment
                # Use a centered flex container to align both logos horizontally
                
                # Read images and convert to base64 for HTML display
                def image_to_base64(image_path: str) -> str:
                    """Convert image file to base64 data URI."""
                    with open(image_path, "rb") as img_file:
                        return base64.b64encode(img_file.read()).decode()
                
                img1_base64 = image_to_base64(company_logo_paths[0])
                img2_base64 = image_to_base64(company_logo_paths[1])
                
                # Create centered flex container with both logos
                logo_html = f"""
                <div style="display: flex; justify-content: center; align-items: center; gap: 10px;">
                    <img src="data:image/png;base64,{img1_base64}" width="120" style="display: block;" />
                    <img src="data:image/png;base64,{img2_base64}" width="120" style="display: block;" />
                </div>
                """
                st.markdown(logo_html, unsafe_allow_html=True)
            else:
                # Single logo
                st.image(company_logo_paths[0], width=120)

    # Initialize session state for history visibility
    if "show_request_history" not in st.session_state:
        st.session_state.show_request_history = False

    # Always show form
    default_requestor = ""
    try:
        default_requestor = fetch_full_name_by_id(path, current_user["id"]) or ""
    except Exception:
        default_requestor = current_user.get("username", "")
    render_request_form(path, current_user["id"], default_requestor)

    # History toggle button and conditional rendering
    st.divider()
    button_label = "📋 Hide Request History" if st.session_state.show_request_history else "📋 Request History"
    if st.button(button_label, key="toggle_history_button", use_container_width=False):
        st.session_state.show_request_history = not st.session_state.show_request_history
        st.rerun()

    # Show history only if toggled on
    if st.session_state.show_request_history:
        render_history(path, current_user)


def render_request_form(
    db_path: str, requester_id: int, requestor_display_name: str = ""
) -> None:
    """Render the form to create a new fuel requisition with auto-calc total."""
    # Initialize session state for duplicate prevention
    if "last_submission_hash" not in st.session_state:
        st.session_state.last_submission_hash = None
    
    # Initialize session state for tracking vehicle/vendor selection
    # Use a reset flag to avoid mutating widget keys after instantiation
    if "reset_request_form" not in st.session_state:
        st.session_state.reset_request_form = False
    if st.session_state.reset_request_form:
        st.session_state.req_vehicle = ""
        st.session_state.req_vendor = ""
        st.session_state.req_fuel_type = None
        st.session_state.last_vehicle_selection = None
        st.session_state.req_qty_mode = "Numeric"
        st.session_state.req_quantity = 0.0
        st.session_state.req_requestor_name = requestor_display_name or ""
        st.session_state.reset_request_form = False

    if "last_vehicle_selection" not in st.session_state:
        st.session_state.last_vehicle_selection = None
    if "req_vendor" not in st.session_state:
        st.session_state.req_vendor = ""  # Empty string for blank selection
    if "req_vehicle" not in st.session_state:
        st.session_state.req_vehicle = ""  # Empty string for blank selection
    if "req_qty_mode" not in st.session_state:
        st.session_state.req_qty_mode = "Numeric"
    if "req_quantity" not in st.session_state:
        st.session_state.req_quantity = 0.0
    if "req_requestor_name" not in st.session_state:
        st.session_state.req_requestor_name = requestor_display_name or ""
    # Show default when unchanged (empty): so the requestor field always displays the default if user has not entered anything
    if not (st.session_state.get("req_requestor_name") or "").strip() and (requestor_display_name or "").strip():
        st.session_state.req_requestor_name = requestor_display_name or ""

    # Form is always visible - load data
    cars = safe_list_cars(db_path)
    vendors = safe_list_vendors(db_path)
    car_map = {f"{c['plate_number']} - {c['model']}": c for c in cars}  # Store full car dict
    vendor_map = {v["name"]: v["id"] for v in vendors}
    vendor_list = list(vendor_map.keys())
    
    # Create mapping from vehicle key to vendor name and fuel_type
    vehicle_to_vendor = {}
    vehicle_to_fuel_type = {}
    for vehicle_key, car_data in car_map.items():
        if car_data.get("vendor_name"):
            vehicle_to_vendor[vehicle_key] = car_data["vendor_name"]
        vehicle_to_fuel_type[vehicle_key] = car_data.get("fuel_type")  # Can be None

    st.subheader("New Request")
    st.caption("💡 Tip: Use Tab or Enter to move between fields")
    
    # Vehicle selection outside form - start with no selection
    vehicle_options = [""] + list(car_map.keys())  # Add empty option at the beginning
    vehicle_choice = st.selectbox(
        "Vehicle", 
        vehicle_options,
        key="req_vehicle", 
        help="Required. Vendor will auto-populate based on vehicle's default vendor."
    )
    
    # Track if vehicle changed (only if a vehicle is actually selected)
    current_vehicle = vehicle_choice if vehicle_choice else None
    last_vehicle = st.session_state.get("last_vehicle_selection")
    vehicle_changed = current_vehicle and current_vehicle != last_vehicle
    
    # Get default vendor for current vehicle (only if vehicle is selected)
    default_vendor = vehicle_to_vendor.get(current_vehicle) if current_vehicle else None
    
    # When vehicle changes, force update vendor, fuel type, and requestor defaults together
    if vehicle_changed and current_vehicle:
        # Vehicle changed - update vendor to vehicle's default
        if default_vendor and default_vendor in vendor_list:
            # Force set vendor in session state - selectbox will use this value
            st.session_state.req_vendor = default_vendor
        elif vendor_list:
            # No default vendor, use first vendor
            st.session_state.req_vendor = vendor_list[0]
        # Populate requestor at same time as vendor and fuel type (below)
        st.session_state.req_requestor_name = requestor_display_name or ""
        # Update tracking
        st.session_state.last_vehicle_selection = current_vehicle
        
        # Check for prior approved requests within 2 days
        vehicle_id = car_map.get(current_vehicle, {}).get("id")
        if vehicle_id:
            try:
                prior_approved = check_prior_approved_requests(db_path, vehicle_id, days=2)
                if prior_approved:
                    # Store prior approved requests in session state to show dialog
                    # Only set if not already shown for this vehicle selection
                    if "prior_approved_notification" not in st.session_state or \
                       st.session_state.prior_approved_notification.get("vehicle") != current_vehicle:
                        st.session_state.prior_approved_notification = {
                            "vehicle": current_vehicle,
                            "requests": prior_approved,
                        }
            except Exception as error:  # pragma: no cover - UI feedback
                # Silently fail - don't block vehicle selection if check fails
                pass
    
    # Show dialog if notification exists (outside the vehicle_changed block to show on rerun)
    if "prior_approved_notification" in st.session_state:
        show_prior_approved_dialog()
    elif not current_vehicle or current_vehicle == "":
        # No vehicle selected - clear vendor
        st.session_state.req_vendor = ""
        st.session_state.last_vehicle_selection = None
    
    # Vendor selection outside form - start with no selection if no vehicle
    vendor_options = [""] + vendor_list  # Add empty option at the beginning
    vendor_index = 0  # Default to empty option
    
    # Only set vendor if vehicle is selected and vendor is set
    if current_vehicle and current_vehicle != "" and st.session_state.req_vendor and st.session_state.req_vendor != "" and st.session_state.req_vendor in vendor_list:
        vendor_index = vendor_list.index(st.session_state.req_vendor) + 1  # +1 because of empty option
    else:
        # No vehicle or no vendor set - use empty option (index 0)
        vendor_index = 0
    
    vendor_choice = st.selectbox(
        "Vendor", 
        vendor_options,
        index=vendor_index,
        key="req_vendor", 
        help="Required. Auto-selected from vehicle's default vendor. You can change it if needed."
    )
    
    # Fuel Type field - pull from vehicle and apply locking logic
    vehicle_fuel_type = vehicle_to_fuel_type.get(current_vehicle) if current_vehicle else None
    
    # Initialize fuel_type in session state
    if "req_fuel_type" not in st.session_state:
        st.session_state.req_fuel_type = None
    
    # Update fuel_type when vehicle changes
    if vehicle_changed and current_vehicle:
        st.session_state.req_fuel_type = vehicle_fuel_type
    elif not current_vehicle or current_vehicle == "":
        st.session_state.req_fuel_type = None
    
    # Determine fuel_type options based on vehicle's fuel_type
    fuel_type_options = []
    fuel_type_disabled = False
    default_fuel_type = st.session_state.req_fuel_type
    
    if vehicle_fuel_type == "Diesel":
        # Diesel: Locked, only Diesel available
        fuel_type_options = ["Diesel"]
        fuel_type_disabled = True
        default_fuel_type = "Diesel"
    elif vehicle_fuel_type == "Unleaded Gasoline":
        # Unleaded: Can switch to Premium
        fuel_type_options = ["Unleaded Gasoline", "Premium Gasoline"]
        fuel_type_disabled = False
        if default_fuel_type not in fuel_type_options:
            default_fuel_type = "Unleaded Gasoline"
    elif vehicle_fuel_type == "Premium Gasoline":
        # Premium: Can switch to Unleaded
        fuel_type_options = ["Premium Gasoline", "Unleaded Gasoline"]
        fuel_type_disabled = False
        if default_fuel_type not in fuel_type_options:
            default_fuel_type = "Premium Gasoline"
    else:
        # NULL fuel_type: All 3 options available
        fuel_type_options = ["Diesel", "Unleaded Gasoline", "Premium Gasoline"]
        fuel_type_disabled = False
        if default_fuel_type not in fuel_type_options:
            default_fuel_type = None
    
    # Set default index
    fuel_type_index = 0
    if default_fuel_type and default_fuel_type in fuel_type_options:
        fuel_type_index = fuel_type_options.index(default_fuel_type)
    
    fuel_type_choice = st.selectbox(
        "Fuel Type",
        fuel_type_options,
        index=fuel_type_index,
        disabled=fuel_type_disabled or not current_vehicle,
        key="req_fuel_type",
        help="Auto-populated from vehicle. Diesel is locked. Gasoline types can be switched."
    )

    with st.form("request_form", clear_on_submit=True):
        qty_mode = st.radio(
            "Quantity Type",
            options=["Numeric", "FULLTANK"],
            index=0 if st.session_state.get("req_qty_mode") != "FULLTANK" else 1,
            key="req_qty_mode",
            horizontal=True,
            help="Choose Numeric to enter liters or FULLTANK for a full tank request.",
        )

        quantity = 0.0
        if qty_mode == "Numeric":
            quantity = st.number_input(
                "Quantity (liters)",
                min_value=0.0,
                step=1.0,
                key="req_quantity",
                help="Press Tab or Enter to move to next field.",
            )
        else:
            st.session_state["req_quantity"] = 0.0

        st.text_input(
            "Requestor",
            key="req_requestor_name",
            help="Required. Defaults to your full name from your account; you can edit it.",
        )

        notes = st.text_area(
            "Notes (optional)", 
            key="req_notes",
            help="Press Tab to move to submit button."
        )
        
        submitted = st.form_submit_button("Submit Request", use_container_width=True)

    if submitted:
        # Get vehicle and vendor from session state (selected outside form)
        # Get quantity, fuel_type and notes from form (they're accessible after form submission)
        vehicle_choice = st.session_state.get("req_vehicle")
        vendor_choice = st.session_state.get("req_vendor")
        fuel_type_choice = st.session_state.get("req_fuel_type")
        qty_mode = st.session_state.get("req_qty_mode")
        quantity = st.session_state.get("req_quantity", 0.0 if qty_mode == "FULLTANK" else 0.0)
        notes = st.session_state.get("req_notes", "")
        requestor_name = (st.session_state.get("req_requestor_name") or requestor_display_name or "").strip()

        # Validate - check for empty strings
        if not requestor_name:
            st.error("Requestor is required.")
            return
        if not vehicle_choice or vehicle_choice == "":
            st.error("Vehicle is required.")
            return
        
        if qty_mode == "Numeric":
            if quantity is None or quantity <= 0:
                st.error("Positive quantity is required for numeric mode.")
                return
        else:
            quantity = 0.0
        
        if not vendor_choice or vendor_choice == "":
            st.error("Vendor is required.")
            return
        
        # Store submission data in session state for dialog
        unit_value = "FULLTANK" if qty_mode == "FULLTANK" else "liters"
        st.session_state.pending_submission = {
            "vehicle": vehicle_choice,
            "vendor": vendor_choice,
            "fuel_type": fuel_type_choice,
            "quantity": quantity,
            "qty_mode": qty_mode,
            "unit_value": unit_value,
            "notes": notes,
            "requestor_name": requestor_name,
            "requester_id": requester_id,
            "db_path": db_path,
            "car_map": car_map,
            "vendor_map": vendor_map,
        }
        # Trigger dialog
        show_submit_confirmation()


@st.dialog("Confirm Request Submission")
def show_submit_confirmation():
    """Show confirmation dialog for request submission."""
    if "pending_submission" not in st.session_state:
        st.error("No pending submission found.")
        return
    
    pending = st.session_state.pending_submission
    vehicle_choice = pending["vehicle"]
    vendor_choice = pending["vendor"]
    fuel_type_choice = pending.get("fuel_type", "—")
    quantity = pending["quantity"]
    qty_mode = pending["qty_mode"]
    notes = pending["notes"]
    
    qty_display = "Full Tank" if qty_mode == "FULLTANK" else f"{quantity} liters"
    
    st.write("**Please review your request details:**")
    st.write(f"**Vehicle:** {vehicle_choice}")
    st.write(f"**Vendor:** {vendor_choice}")
    st.write(f"**Fuel Type:** {fuel_type_choice}")
    st.write(f"**Quantity:** {qty_display}")
    requestor_name = pending.get("requestor_name", "").strip()
    if requestor_name:
        st.write(f"**Requestor:** {requestor_name}")
    if notes and notes.strip():
        st.write(f"**Notes:** {notes.strip()}")
    st.write("")
    st.write("Are you sure you want to submit this request?")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Submit", use_container_width=True, key="confirm_submit"):
        # Create a hash of the submission to prevent duplicates
        submission_data = f"{pending['requester_id']}_{vehicle_choice}_{vendor_choice}_{quantity}_{pending['unit_value']}_{pending.get('requestor_name','')}_{notes}"
        submission_hash = hashlib.md5(submission_data.encode()).hexdigest()
        
        # Check if this exact submission was already processed
        if st.session_state.get("last_submission_hash") == submission_hash:
            st.warning("This request was already submitted. Please refresh the page if you want to submit a new request.")
        else:
            vehicle_id = pending["car_map"].get(vehicle_choice, {}).get("id")
            vendor_id = pending["vendor_map"].get(vendor_choice)
            try:
                create_requisition(
                    db_path=pending["db_path"],
                    requester_id=pending["requester_id"],
                    vehicle_id=vehicle_id,
                    vendor_id=vendor_id,
                    quantity=quantity,
                    unit=pending["unit_value"],
                    unit_price=None,
                    notes=notes.strip() if notes else "",
                    fuel_type=fuel_type_choice,
                    requestor_name=pending.get("requestor_name", "").strip() or None,
                )
                # Store the submission hash to prevent duplicates
                st.session_state.last_submission_hash = submission_hash
                # Signal form reset for next render (avoid mutating widget keys mid-run)
                st.session_state.reset_request_form = True
                # Clear pending submission
                del st.session_state.pending_submission
                st.success("Request submitted.")
                st.rerun()
            except Exception as error:  # pragma: no cover - user-facing
                st.error(str(error))
    
    if col2.button("Cancel", use_container_width=True, key="cancel_submit"):
        # Clear pending submission
        if "pending_submission" in st.session_state:
            del st.session_state.pending_submission
        st.rerun()


@st.dialog("Prior Approved Request Notification")
def show_prior_approved_dialog():
    """Show notification dialog when vehicle has prior approved requests within 2 days."""
    if "prior_approved_notification" not in st.session_state:
        return
    
    notification = st.session_state.prior_approved_notification
    vehicle = notification["vehicle"]
    requests = notification["requests"]
    
    st.warning(f"⚠️ **Notice:** The selected vehicle **{vehicle}** has {len(requests)} prior approved request(s) within the last 2 days.")
    st.write("")
    st.write("**Prior Approved Requests:**")
    
    # Display the requests in a table format
    for req in requests:
        qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req.get('quantity', 0)} liters"
        st.write(f"• **Serial # {req.get('serial_number', '—')}** - {qty_text} - {req.get('vendor_name', '—')} - {req.get('updated_at', '—')}")
    
    st.write("")
    st.info("💡 You can still proceed with creating a new request if needed.")
    
    if st.button("OK, I Understand", use_container_width=True, key="prior_approved_ok"):
        # Clear notification
        if "prior_approved_notification" in st.session_state:
            del st.session_state.prior_approved_notification
        st.rerun()


def render_history(db_path: str, current_user: Dict[str, str]) -> None:
    """
    Display the user's requisition history with edit buttons.

    Args:
        db_path: Database path.
        current_user: Dict with user context (id, username, role).
    """
    requester_id = current_user["id"]
    st.subheader("Request History")
    requests = safe_list_user_requisitions(db_path, requester_id)
    if not requests:
        st.info("No requests yet.")
        return

    # Header row
    header_cols = st.columns([1.5, 2, 2, 2, 2, 2, 1, 1])
    header_cols[0].markdown("**Serial #**")
    header_cols[1].markdown("**Vehicle**")
    header_cols[2].markdown("**Quantity**")
    header_cols[3].markdown("**Vendor**")
    header_cols[4].markdown("**Total Price**")
    header_cols[5].markdown("**Status**")
    header_cols[6].markdown("**Date**")
    header_cols[7].markdown("**Action**")
    st.divider()

    for req in requests:
        cols = st.columns([1.5, 2, 2, 2, 2, 2, 1, 1])
        cols[0].markdown(f"**{req.get('serial_number', '—')}**")
        cols[1].markdown(f"**{req['plate_number']}**")
        qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
        cols[2].write(qty_text)
        cols[3].write(req.get("vendor_name") or "—")
        if req.get("total_price"):
            cols[4].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[4].write("—")
        cols[5].write(req["status"].title())
        cols[6].write(req["created_at"])
        
        # Edit button
        req_id = req["id"]
        can_edit, error_msg = can_user_edit_requisition(
            db_path, req_id, current_user["id"], current_user["role"]
        )
        
        if can_edit:
            if cols[7].button("Edit", key=f"edit_{req_id}", use_container_width=True):
                st.session_state[f"editing_{req_id}"] = True
                st.rerun()
        else:
            # Show disabled state or tooltip
            cols[7].write("—")
            if req.get("is_edited", 0) == 1:
                cols[7].caption("Already edited")
            elif req.get("status", "").lower() != "pending":
                cols[7].caption("Not pending")
        
        # Show edit form if this request is being edited
        if st.session_state.get(f"editing_{req_id}", False):
            st.divider()
            render_edit_form(db_path, req_id, current_user, req)
            st.divider()
        
        if req.get("notes"):
            st.caption(req["notes"])


def render_edit_form(
    db_path: str, requisition_id: int, current_user: Dict[str, str], req: dict
) -> None:
    """
    Render the edit form for a requisition.

    Args:
        db_path: Database path.
        requisition_id: ID of the requisition to edit.
        current_user: Dict with user context (id, username, role).
        req: Current requisition data.
    """
    st.subheader(f"Edit Request - Serial # {req.get('serial_number', '—')}")
    
    # Fetch full requisition details
    full_req = fetch_requisition_by_id(db_path, requisition_id)
    if not full_req:
        st.error("Requisition not found.")
        return
    
    cars = safe_list_cars(db_path)
    vendors = safe_list_vendors(db_path)
    car_map = {f"{c['plate_number']} - {c['model']}": c["id"] for c in cars}
    car_data_map = {f"{c['plate_number']} - {c['model']}": c for c in cars}
    vendor_map = {v["name"]: v["id"] for v in vendors}
    
    # Find current selections
    current_vehicle_key = f"{full_req['plate_number']} - {full_req['model']}"
    current_fuel_type = full_req.get("fuel_type") or ""
    current_vendor_name = full_req.get("vendor_name") or ""
    
    # Get index for selectbox
    vehicle_options = list(car_map.keys())
    vendor_options = list(vendor_map.keys())
    
    try:
        vehicle_index = vehicle_options.index(current_vehicle_key) if current_vehicle_key in vehicle_options else 0
        vendor_index = vendor_options.index(current_vendor_name) if current_vendor_name in vendor_options else 0
    except (ValueError, KeyError):
        vehicle_index = 0
        vendor_index = 0
    
    # Get vehicle's fuel_type for locking logic
    current_vehicle_data = car_data_map.get(current_vehicle_key, {})
    vehicle_fuel_type = current_vehicle_data.get("fuel_type")  # From vehicle master data
    
    # Determine fuel_type options based on vehicle's fuel_type
    fuel_type_options = []
    fuel_type_disabled = False
    edit_fuel_type_index = 0
    
    if vehicle_fuel_type == "Diesel":
        # Diesel: Locked, only Diesel available
        fuel_type_options = ["Diesel"]
        fuel_type_disabled = True
        edit_fuel_type_index = 0
    elif vehicle_fuel_type == "Unleaded Gasoline":
        # Unleaded: Can switch to Premium
        fuel_type_options = ["Unleaded Gasoline", "Premium Gasoline"]
        fuel_type_disabled = False
        if current_fuel_type in fuel_type_options:
            edit_fuel_type_index = fuel_type_options.index(current_fuel_type)
        else:
            edit_fuel_type_index = 0  # Default to Unleaded
    elif vehicle_fuel_type == "Premium Gasoline":
        # Premium: Can switch to Unleaded
        fuel_type_options = ["Premium Gasoline", "Unleaded Gasoline"]
        fuel_type_disabled = False
        if current_fuel_type in fuel_type_options:
            edit_fuel_type_index = fuel_type_options.index(current_fuel_type)
        else:
            edit_fuel_type_index = 0  # Default to Premium
    else:
        # NULL fuel_type: All 3 options available
        fuel_type_options = ["Diesel", "Unleaded Gasoline", "Premium Gasoline"]
        fuel_type_disabled = False
        if current_fuel_type in fuel_type_options:
            edit_fuel_type_index = fuel_type_options.index(current_fuel_type)
        else:
            edit_fuel_type_index = 0  # Default to first option
    
    with st.form(f"edit_form_{requisition_id}", clear_on_submit=False):
        vehicle_choice = st.selectbox(
            "Vehicle",
            vehicle_options,
            index=vehicle_index,
            key=f"edit_vehicle_{requisition_id}",
            help="Required. Press Tab to move to next field.",
        )
        vendor_choice = st.selectbox(
            "Vendor",
            vendor_options,
            index=vendor_index,
            key=f"edit_vendor_{requisition_id}",
            help="Required. Press Tab to move to next field.",
        )
        fuel_type_choice = st.selectbox(
            "Fuel Type",
            fuel_type_options,
            index=edit_fuel_type_index,
            disabled=fuel_type_disabled,
            key=f"edit_fuel_type_{requisition_id}",
            help="Auto-populated from vehicle. Diesel is locked. Gasoline types can be switched.",
        )
        initial_mode = "FULLTANK" if full_req.get("unit", "").upper() == "FULLTANK" else "Numeric"
        qty_mode = st.radio(
            "Quantity Type",
            options=["Numeric", "FULLTANK"],
            index=0 if initial_mode != "FULLTANK" else 1,
            key=f"edit_qty_mode_{requisition_id}",
            horizontal=True,
            help="Choose Numeric to enter liters or FULLTANK for a full tank request.",
        )
        quantity = 0.0
        if qty_mode == "Numeric":
            quantity = st.number_input(
                "Quantity (liters)",
                min_value=0.0,
                step=1.0,
                value=float(full_req.get("quantity", 0)),
                key=f"edit_quantity_{requisition_id}",
                help="Press Tab or Enter to move to next field.",
            )
        st.text_input(
            "Requestor",
            value=full_req.get("requestor_name") or "—",
            disabled=True,
            key=f"edit_requestor_{requisition_id}",
            help="From the user who created this request (full name).",
        )
        notes = st.text_area(
            "Notes (optional)",
            value=full_req.get("notes") or "",
            key=f"edit_notes_{requisition_id}",
            help="Press Tab to move to submit button.",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    
    if cancelled:
        st.session_state[f"editing_{requisition_id}"] = False
        st.rerun()
    
    if submitted:
        notes = st.session_state.get(f"edit_notes_{requisition_id}", "") or ""
        if not vehicle_choice or not vendor_choice or vendor_choice == "(None)":
            st.error("Vehicle and vendor are required.")
            return
        if qty_mode == "Numeric":
            if quantity is None or quantity <= 0:
                st.error("Positive quantity is required for numeric mode.")
                return
        else:
            quantity = 0.0
        
        vehicle_id = car_map.get(vehicle_choice)
        vendor_id = vendor_map.get(vendor_choice)
        fuel_type_value = st.session_state.get(f"edit_fuel_type_{requisition_id}")
        
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
                unit_price=None,  # Unit price is set by purchaser, not in edit form
                notes=notes.strip(),
                fuel_type=fuel_type_value,
            )
            st.session_state[f"editing_{requisition_id}"] = False
            st.success("Request updated successfully.")
            st.rerun()
        except Exception as error:  # pragma: no cover - user-facing
            st.error(str(error))


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

