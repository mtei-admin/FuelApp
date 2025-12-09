"""Master data management screen (vendors and cars)."""
from pathlib import Path
from typing import List, Optional

import streamlit as st

from src.database import (
    list_cars,
    list_vendors,
    soft_delete_car,
    soft_delete_vendor,
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

    render_vendors_section(path)
    st.divider()
    render_cars_section(path)


def render_vendors_section(db_path: str) -> None:
    """Render vendor creation and list with soft delete actions."""
    st.subheader("Vendors")
    with st.form("vendor_form"):
        name = st.text_input("Vendor name", key="vendor_name")
        contact = st.text_input("Contact (optional)", key="vendor_contact")
        submitted = st.form_submit_button("Save Vendor")
    if submitted:
        if not name.strip():
            st.error("Vendor name is required.")
        else:
            try:
                upsert_vendor(db_path, name.strip(), contact.strip())
                st.success("Vendor saved.")
                st.rerun()
            except Exception as error:  # pragma: no cover - shown to user
                st.error(str(error))

    vendors = safe_list_vendors(db_path)
    if not vendors:
        st.info("No active vendors yet.")
        return

    for vendor in vendors:
        cols = st.columns([3, 3, 1])
        cols[0].markdown(f"**{vendor['name']}**")
        cols[1].write(vendor.get("contact", ""))
        if cols[2].button(
            "Deactivate",
            key=f"deactivate_vendor_{vendor['id']}",
            help="Soft delete vendor",
        ):
            soft_delete_vendor(db_path, vendor["id"])
            st.rerun()


def render_cars_section(db_path: str) -> None:
    """Render car creation and list with soft delete actions."""
    st.subheader("Cars")
    vendors = safe_list_vendors(db_path)
    vendor_options = {v["name"]: v["id"] for v in vendors}

    with st.form("car_form"):
        plate = st.text_input("Plate number", key="car_plate")
        model = st.text_input("Model", key="car_model")
        vendor_name = st.selectbox(
            "Vendor (optional)", ["(None)"] + list(vendor_options.keys()), key="car_vendor"
        )
        submitted = st.form_submit_button("Save Car")

    if submitted:
        if not plate.strip() or not model.strip():
            st.error("Plate number and model are required.")
        else:
            vendor_id = vendor_options.get(vendor_name) if vendor_name != "(None)" else None
            try:
                upsert_car(db_path, plate.strip(), model.strip(), vendor_id)
                st.success("Car saved.")
                st.rerun()
            except Exception as error:  # pragma: no cover - shown to user
                st.error(str(error))

    cars = safe_list_cars(db_path)
    if not cars:
        st.info("No active cars yet.")
        return

    for car in cars:
        cols = st.columns([2, 3, 2, 1])
        cols[0].markdown(f"**{car['plate_number']}**")
        cols[1].write(car["model"])
        cols[2].write(car.get("vendor_name") or "—")
        if cols[3].button(
            "Deactivate",
            key=f"deactivate_car_{car['id']}",
            help="Soft delete car",
        ):
            soft_delete_car(db_path, car["id"])
            st.rerun()


def safe_list_vendors(db_path: str) -> List[dict]:
    """Safely list vendors; return empty list on error with user feedback."""
    try:
        return list_vendors(db_path) if list_vendors else []
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load vendors: {error}")
        return []


def safe_list_cars(db_path: str) -> List[dict]:
    """Safely list cars; return empty list on error with user feedback."""
    try:
        return list_cars(db_path) if list_cars else []
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load cars: {error}")
        return []

