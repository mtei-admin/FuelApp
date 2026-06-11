"""Master data management screen (vendors and cars)."""
from pathlib import Path
from typing import List, Optional

import streamlit as st

from src.database import (
    list_cars,
    list_vendors,
    soft_delete_car,
    soft_delete_vendor,
    update_car,
    update_vendor,
    upsert_car,
    upsert_vendor,
)

# Path provided by app; fallback for standalone preview
DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None) -> None:
    """
    Render the master data management UI for vendors and cars.

    Args:
        db_path: Optional override for the SQLite database path.
    """
    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Master Data")
    st.caption("Manage vendors and vehicles (soft delete only).")

    # Slightly enlarge tab labels for better visibility on this page
    st.markdown(
        """
        <style>
        div[data-baseweb="tab-list"] button[role="tab"] {
            font-size: 1.50rem;
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    vendor_tab, vehicle_tab = st.tabs(["Vendors", "Vehicles"])

    with vendor_tab:
        render_vendors_section(path)

    with vehicle_tab:
        render_vehicles_section(path)


def render_vendors_section(db_path: str) -> None:
    """Render vendor creation and list with soft delete actions."""
    st.subheader("Vendors")
    
    # Initialize session state for form visibility
    if "show_vendor_form" not in st.session_state:
        st.session_state.show_vendor_form = False
    
    # ADD ENTRY link/button
    if st.button("➕ ADD ENTRY", key="add_vendor_button", use_container_width=False):
        st.session_state.show_vendor_form = True
        st.rerun()
    
    # Show form only if session state is True
    if st.session_state.show_vendor_form:
        with st.form("vendor_form"):
            name = st.text_input("Vendor name", key="vendor_name")
            address = st.text_input("Address (optional)", key="vendor_address")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Save Vendor", use_container_width=True)
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancelled:
            st.session_state.show_vendor_form = False
            st.rerun()
        
        if submitted:
            if not name.strip():
                st.error("Vendor name is required.")
            else:
                try:
                    upsert_vendor(db_path, name.strip(), address.strip())
                    st.session_state.show_vendor_form = False
                    st.success("Vendor saved.")
                    st.rerun()
                except Exception as error:  # pragma: no cover - shown to user
                    st.error(str(error))
    
    st.divider()
    vendors = safe_list_vendors(db_path)
    if not vendors:
        st.info("No active vendors yet.")
        return

    for vendor in vendors:
        cols = st.columns([3, 3, 1, 1])
        cols[0].markdown(f"**{vendor['name']}**")
        cols[1].write(vendor.get("address", ""))
        
        # Edit button
        if cols[2].button(
            "Edit",
            key=f"edit_vendor_{vendor['id']}",
            help="Edit vendor",
        ):
            st.session_state[f"editing_vendor_{vendor['id']}"] = True
            st.rerun()
        
        # Deactivate button
        if cols[3].button(
            "Deactivate",
            key=f"deactivate_vendor_{vendor['id']}",
            help="Soft delete vendor",
        ):
            soft_delete_vendor(db_path, vendor["id"])
            st.rerun()
        
        # Show edit form if this vendor is being edited
        if st.session_state.get(f"editing_vendor_{vendor['id']}", False):
            st.divider()
            render_edit_vendor_form(db_path, vendor)
            st.divider()


def render_vehicles_section(db_path: str) -> None:
    """Render vehicle creation and list with soft delete actions."""
    st.subheader("Vehicle")
    
    # Initialize session state for form visibility
    if "show_vehicle_form" not in st.session_state:
        st.session_state.show_vehicle_form = False
    
    # ADD ENTRY link/button
    if st.button("➕ ADD ENTRY", key="add_vehicle_button", use_container_width=False):
        st.session_state.show_vehicle_form = True
        st.rerun()
    
    # Show form only if session state is True
    if st.session_state.show_vehicle_form:
        vendors = safe_list_vendors(db_path)
        vendor_options = {v["name"]: v["id"] for v in vendors}

        with st.form("vehicle_form"):
            plate = st.text_input("Plate number", key="vehicle_plate")
            model = st.text_input("Model", key="vehicle_model")
            fuel_type = st.selectbox(
                "Fuel Type",
                ["Diesel", "Unleaded Gasoline", "Premium Gasoline"],
                key="vehicle_fuel_type"
            )
            company = st.selectbox(
                "Company",
                ["MTEI", "DSRDC", "DIC", "GCEIC", "MTEI Trucking"],
                key="vehicle_company"
            )
            vendor_name = st.selectbox(
                "Vendor (optional)", ["(None)"] + list(vendor_options.keys()), key="vehicle_vendor"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Save Vehicle", use_container_width=True)
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if cancelled:
            st.session_state.show_vehicle_form = False
            st.rerun()

        if submitted:
            if not plate.strip() or not model.strip():
                st.error("Plate number and model are required.")
            elif not fuel_type:
                st.error("Fuel type is required.")
            elif not company:
                st.error("Company is required.")
            else:
                vendor_id = vendor_options.get(vendor_name) if vendor_name != "(None)" else None
                try:
                    upsert_car(db_path, plate.strip(), model.strip(), vendor_id, fuel_type, company)
                    st.session_state.show_vehicle_form = False
                    st.success("Vehicle saved.")
                    st.rerun()
                except Exception as error:  # pragma: no cover - shown to user
                    st.error(str(error))
    
    st.divider()
    vehicles = safe_list_vehicles(db_path)
    if not vehicles:
        st.info("No active vehicles yet.")
        return

    # Header row
    header_cols = st.columns([2, 3, 2, 1, 1])
    header_cols[0].markdown("**Plate Number**")
    header_cols[1].markdown("**Make/Model**")
    header_cols[2].markdown("**Default Vendor**")
    header_cols[3].markdown("**Action**")
    header_cols[4].markdown("**Action**")
    st.divider()

    for vehicle in vehicles:
        cols = st.columns([2, 3, 2, 1, 1])
        cols[0].markdown(f"**{vehicle['plate_number']}**")
        cols[1].write(vehicle["model"])
        cols[2].write(vehicle.get("vendor_name") or "—")
        
        # Edit button
        if cols[3].button(
            "Edit",
            key=f"edit_vehicle_{vehicle['id']}",
            help="Edit vehicle",
        ):
            st.session_state[f"editing_vehicle_{vehicle['id']}"] = True
            st.rerun()
        
        # Deactivate button
        if cols[4].button(
            "Deactivate",
            key=f"deactivate_vehicle_{vehicle['id']}",
            help="Soft delete vehicle",
        ):
            soft_delete_car(db_path, vehicle["id"])
            st.rerun()
        
        # Show edit form if this vehicle is being edited
        if st.session_state.get(f"editing_vehicle_{vehicle['id']}", False):
            st.divider()
            render_edit_vehicle_form(db_path, vehicle)
            st.divider()


def safe_list_vendors(db_path: str) -> List[dict]:
    """Safely list vendors; return empty list on error with user feedback."""
    try:
        return list_vendors(db_path) if list_vendors else []
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load vendors: {error}")
        return []


def render_edit_vendor_form(db_path: str, vendor: dict) -> None:
    """
    Render the edit form for a vendor.

    Args:
        db_path: Database path.
        vendor: Current vendor data.
    """
    st.subheader(f"Edit Vendor - {vendor['name']}")
    
    with st.form(f"edit_vendor_form_{vendor['id']}", clear_on_submit=False):
        name = st.text_input(
            "Vendor name",
            value=vendor.get("name", ""),
            key=f"edit_vendor_name_{vendor['id']}",
        )
        address = st.text_input(
            "Address (optional)",
            value=vendor.get("address", ""),
            key=f"edit_vendor_address_{vendor['id']}",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    
    if cancelled:
        st.session_state[f"editing_vendor_{vendor['id']}"] = False
        st.rerun()
    
    if submitted:
        if not name.strip():
            st.error("Vendor name is required.")
        else:
            try:
                update_vendor(db_path, vendor["id"], name.strip(), address.strip())
                st.session_state[f"editing_vendor_{vendor['id']}"] = False
                st.success("Vendor updated successfully.")
                st.rerun()
            except Exception as error:  # pragma: no cover - shown to user
                st.error(str(error))


def render_edit_vehicle_form(db_path: str, vehicle: dict) -> None:
    """
    Render the edit form for a vehicle.

    Args:
        db_path: Database path.
        vehicle: Current vehicle data.
    """
    st.subheader(f"Edit Vehicle - {vehicle['plate_number']}")
    
    vendors = safe_list_vendors(db_path)
    vendor_options = {v["name"]: v["id"] for v in vendors}
    
    # Find current vendor selection
    current_vendor_name = vehicle.get("vendor_name") or "(None)"
    vendor_options_list = ["(None)"] + list(vendor_options.keys())
    try:
        vendor_index = vendor_options_list.index(current_vendor_name) if current_vendor_name in vendor_options_list else 0
    except (ValueError, KeyError):
        vendor_index = 0
    
    with st.form(f"edit_vehicle_form_{vehicle['id']}", clear_on_submit=False):
        plate = st.text_input(
            "Plate number",
            value=vehicle.get("plate_number", ""),
            key=f"edit_vehicle_plate_{vehicle['id']}",
        )
        model = st.text_input(
            "Model",
            value=vehicle.get("model", ""),
            key=f"edit_vehicle_model_{vehicle['id']}",
        )
        # Fuel type dropdown (required)
        fuel_type_options = ["Diesel", "Unleaded Gasoline", "Premium Gasoline"]
        current_fuel_type = vehicle.get("fuel_type") or "Diesel"
        try:
            fuel_type_index = fuel_type_options.index(current_fuel_type) if current_fuel_type in fuel_type_options else 0
        except (ValueError, KeyError):
            fuel_type_index = 0
        
        fuel_type = st.selectbox(
            "Fuel Type",
            fuel_type_options,
            index=fuel_type_index,
            key=f"edit_vehicle_fuel_type_{vehicle['id']}",
        )
        # Company dropdown (required)
        company_options = ["MTEI", "DSRDC", "DIC", "GCEIC", "MTEI Trucking"]
        current_company = vehicle.get("company") or "MTEI"
        try:
            company_index = company_options.index(current_company) if current_company in company_options else 0
        except (ValueError, KeyError):
            company_index = 0
        
        company = st.selectbox(
            "Company",
            company_options,
            index=company_index,
            key=f"edit_vehicle_company_{vehicle['id']}",
        )
        vendor_name = st.selectbox(
            "Vendor (optional)",
            vendor_options_list,
            index=vendor_index,
            key=f"edit_vehicle_vendor_{vehicle['id']}",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    
    if cancelled:
        st.session_state[f"editing_vehicle_{vehicle['id']}"] = False
        st.rerun()
    
    if submitted:
        if not plate.strip() or not model.strip():
            st.error("Plate number and model are required.")
        elif not fuel_type:
            st.error("Fuel type is required.")
        elif not company:
            st.error("Company is required.")
        else:
            vendor_id = vendor_options.get(vendor_name) if vendor_name != "(None)" else None
            try:
                update_car(db_path, vehicle["id"], plate.strip(), model.strip(), vendor_id, fuel_type, company)
                st.session_state[f"editing_vehicle_{vehicle['id']}"] = False
                st.success("Vehicle updated successfully.")
                st.rerun()
            except Exception as error:  # pragma: no cover - shown to user
                st.error(str(error))


def safe_list_vehicles(db_path: str) -> List[dict]:
    """Safely list vehicles; return empty list on error with user feedback."""
    try:
        return list_cars(db_path) if list_cars else []
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load vehicles: {error}")
        return []

