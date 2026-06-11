"""Purchasing screen for generating purchase orders and marking receipt."""
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from src.database import (
    fetch_full_name_by_id,
    get_vendor_fuel_prices,
    get_vendor_fuel_price_for_fuel_type,
    list_requisitions_by_status,
    update_requisition_po,
    update_requisition_received,
    upsert_vendor_fuel_prices,
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
    if current_user.get("role", "").lower() not in {"purchaser", "accounting", "superuser"}:
        st.error("You do not have permission to view purchasing.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Purchasing")
    st.caption("Generate POs for approved requests and mark receipts.")

    # Allow fuel price updates anytime (all purchasing-access roles except plain "user").
    role = current_user.get("role", "").lower()
    if role != "user":
        if st.button("Update Fuel Prices", key="update_fuel_prices_anytime"):
            st.session_state["price_update_prompt_shown"] = True
            st.session_state["show_price_update_dialog"] = True
            st.session_state["fuel_prices_updated"] = False
            st.rerun()

    # Once per session: ask purchaser if they have fuel price updates
    _maybe_show_price_update_prompt(current_user)

    # If dialog was requested, open the price-update dialog
    if st.session_state.get("show_price_update_dialog"):
        _open_price_update_dialog(path, current_user)

    render_po_generation(path, current_user)
    st.divider()
    render_receiving(path)


def _maybe_show_price_update_prompt(current_user: Dict[str, str]) -> None:
    """If user is purchaser and not yet prompted this session, show modal prompt."""
    if current_user.get("role", "").lower() != "purchaser":
        return
    if st.session_state.get("price_update_prompt_shown"):
        return

    _open_price_update_prompt_dialog()


@st.dialog("Fuel price update required")
def _open_price_update_prompt_dialog() -> None:
    """Blocking centered prompt asking whether to enter fuel price updates."""
    st.markdown(
        """
        <div style="text-align: center; font-size: 20px; font-weight: 800; margin-bottom: 8px;">
            Fuel Price Update
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("Do you have fuel price updates to enter? (This affects PO unit pricing.)")

    col_yes, col_no = st.columns([1, 1])
    with col_yes:
        if st.button("Yes, enter updates", key="price_update_prompt_yes"):
            st.session_state["price_update_prompt_shown"] = True
            st.session_state["show_price_update_dialog"] = True
            st.rerun()
    with col_no:
        if st.button("No, skip", key="price_update_prompt_no"):
            st.session_state["price_update_prompt_shown"] = True
            st.session_state["show_price_update_dialog"] = False
            st.rerun()


@st.dialog("Fuel price updates by vendor")
def _open_price_update_dialog(db_path: str, current_user: Dict[str, str]) -> None:
    """Dialog with one tab per vendor; each tab has Diesel/Unleaded/Premium and Update button."""
    # Track whether any updates were applied during this dialog session.
    st.session_state["fuel_prices_updated"] = False
    vendors_with_prices = get_vendor_fuel_prices(db_path)
    if not vendors_with_prices:
        st.info("No active vendors. Add vendors in Master Data first.")
        if st.button("Close", key="price_dialog_close"):
            st.session_state["show_price_update_dialog"] = False
            st.rerun()
        return

    tab_names = [v.get("vendor_name") or f"Vendor {v.get('vendor_id')}" for v in vendors_with_prices]
    tabs = st.tabs(tab_names)
    user_id = current_user.get("id")
    try:
        uid = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        uid = None

    for idx, (tab, row) in enumerate(zip(tabs, vendors_with_prices)):
        with tab:
            vendor_id = row["vendor_id"]
            diesel = st.number_input(
                "Diesel (₱/liter)",
                min_value=0.0,
                value=float(row.get("diesel_price") or 0),
                step=0.01,
                format="%.2f",
                key=f"fp_diesel_{vendor_id}",
            )
            unleaded = st.number_input(
                "Gasoline Unleaded (₱/liter)",
                min_value=0.0,
                value=float(row.get("unleaded_price") or 0),
                step=0.01,
                format="%.2f",
                key=f"fp_unleaded_{vendor_id}",
            )
            premium = st.number_input(
                "Gasoline Premium (₱/liter)",
                min_value=0.0,
                value=float(row.get("premium_price") or 0),
                step=0.01,
                format="%.2f",
                key=f"fp_premium_{vendor_id}",
            )
            _, btn_col = st.columns([3, 1])
            with btn_col:
                if st.button("Update", key=f"fp_update_{vendor_id}"):
                    try:
                        upsert_vendor_fuel_prices(
                            db_path,
                            vendor_id,
                            diesel if diesel > 0 else None,
                            unleaded if unleaded > 0 else None,
                            premium if premium > 0 else None,
                            uid,
                        )
                        st.success("Prices updated.")
                        st.session_state["fuel_prices_updated"] = True
                        st.session_state["price_update_prompt_shown"] = True
                        st.rerun()
                    except Exception as err:
                        st.error(str(err))

    st.divider()
    if st.button("Done", key="price_dialog_done"):
        st.session_state["show_price_update_dialog"] = False
        st.rerun()


def render_po_generation(db_path: str, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    List approved requests and allow PO generation.
    
    Args:
        db_path: Database path.
        current_user: Optional user context for tracking who prepared the PO.
    """
    st.subheader("Approved Requests (Generate PO)")
    approved = safe_list_by_status(db_path, ["approved"])
    if not approved:
        st.info("No approved requests awaiting PO.")
        return

    # Header row
    header_cols = st.columns([1.5, 3, 2, 2.5, 2, 2, 3])
    header_cols[0].markdown("**Serial #**")
    header_cols[1].markdown("**Vehicle — Vendor**")
    header_cols[2].markdown("**Quantity**")
    header_cols[3].markdown("**Unit Price**")
    header_cols[4].markdown("**Total Price**")
    header_cols[5].markdown("**Requested By**")
    header_cols[6].markdown("**PO Ref / Action**")
    st.divider()

    for req in approved:
        cols = st.columns([1.5, 3, 2, 2.5, 2, 2, 3])
        cols[0].markdown(f"**{req.get('serial_number', '—')}**")
        cols[1].markdown(f"**{req['plate_number']}** — {req.get('vendor_name') or '—'}")
        qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
        cols[2].write(qty_text)

        # Default unit price from current vendor fuel price (by fuel type), else existing or 0
        current_unit_price = get_vendor_fuel_price_for_fuel_type(
            db_path, req.get("vendor_id"), req.get("fuel_type")
        )
        default_price = float(
            current_unit_price if current_unit_price is not None else req.get("unit_price") or 0
        )
        unit_price = cols[3].number_input(
            "Current unit price (₱/liter)",
            min_value=0.0,
            step=0.01,
            value=default_price,
            key=f"unit_price_{req['id']}",
            format="%.2f",
            label_visibility="collapsed",
            help="From vendor fuel prices; editable.",
        )
        
        # Calculate and display total price
        total_price = None
        if req.get("unit", "").upper() != "FULLTANK" and unit_price > 0:
            total_price = req['quantity'] * unit_price
        if total_price:
            cols[4].write(f"₱{total_price:,.2f}")
        else:
            cols[4].write("—")
        
        cols[5].write(req.get('requester_name') or '—')
        po_ref = cols[6].text_input(
            "PO Ref (optional)",
            key=f"po_ref_{req['id']}",
            placeholder="PO-12345",
        )
        # Check if PDF is ready for download (after confirmation)
        pdf_key = f"po_pdf_ready_{req['id']}"
        if st.session_state.get(pdf_key):
            pdf_data = st.session_state.get(f"po_pdf_data_{req['id']}")
            pdf_filename = st.session_state.get(f"po_pdf_filename_{req['id']}")
            if pdf_data and pdf_filename:
                # Show custom download icon above a minimal download button
                cols[6].image("assets/download_icon.png", width=28)
                cols[6].download_button(
                    "Download",
                    data=pdf_data,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key=f"po_dl_{req['id']}",
                )
                # Clear the ready flag after showing download button
                if cols[6].button("Clear", key=f"clear_po_{req['id']}"):
                    st.session_state[pdf_key] = False
                    st.session_state[f"po_pdf_data_{req['id']}"] = None
                    st.session_state[f"po_pdf_filename_{req['id']}"] = None
                    st.rerun()
        elif cols[6].button("Generate PO & Download", key=f"po_btn_{req['id']}"):
            if unit_price <= 0:
                st.error("Unit price is required to generate PO.")
            else:
                # Store PO generation data in session state for dialog
                st.session_state.pending_po_generation = {
                    "req_id": req["id"],
                    "req": req,
                    "db_path": db_path,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "po_ref": po_ref.strip(),
                    "pdf_key": pdf_key,
                    "current_user": current_user,
                }
                # Trigger dialog
                show_po_confirmation()


@st.dialog("Confirm PO Generation")
def show_po_confirmation():
    """Show confirmation dialog for PO generation."""
    if "pending_po_generation" not in st.session_state:
        st.error("No pending PO generation found.")
        return
    
    pending = st.session_state.pending_po_generation
    req = pending["req"]
    unit_price = pending["unit_price"]
    total_price = pending["total_price"]
    po_ref = pending["po_ref"]
    
    qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
    po_ref_display = po_ref if po_ref else "(No PO Reference)"
    
    # Recalculate total_price if needed (in case it wasn't calculated in the main view)
    if total_price is None and unit_price > 0 and req.get("unit", "").upper() != "FULLTANK":
        total_price = req['quantity'] * unit_price
    
    total_price_display = f"₱{total_price:,.2f}" if total_price is not None and total_price > 0 else "—"
    
    st.write("**Please review the PO details:**")
    st.write(f"**Serial #:** {req.get('serial_number', '—')}")
    st.write(f"**Vehicle:** {req['plate_number']}")
    st.write(f"**Vendor:** {req.get('vendor_name') or '—'}")
    st.write(f"**Quantity:** {qty_text}")
    st.write(f"**Unit Price:** ₱{unit_price:,.2f}")
    st.write(f"**Total Price:** {total_price_display}")
    st.write(f"**PO Reference:** {po_ref_display}")
    st.write("")
    st.write("Are you sure you want to generate and download this PO?")
    
    col1, col2 = st.columns(2)
    if col1.button("Yes, Generate", use_container_width=True, key=f"confirm_po_{req['id']}"):
        try:
            # Get current user from pending data or session state
            current_user = pending.get("current_user") or st.session_state.get("current_user", {})
            prepared_by_user_id = current_user.get("id") if current_user else None
            
            # Update requisition with unit_price and calculate total
            update_requisition_po(pending["db_path"], req["id"], po_ref, unit_price, prepared_by_user_id)
            # Update req dict for PDF generation (prepared_by is in DB but req is pre-update; set it for the PDF)
            req["unit_price"] = unit_price
            req["total_price"] = total_price
            req["prepared_by"] = (
                fetch_full_name_by_id(pending["db_path"], prepared_by_user_id)
                if prepared_by_user_id
                else (current_user.get("username") or "")
            )
            pdf_bytes = build_po_pdf(pending["db_path"], req, po_ref)
            # Store PDF in session state for download
            pdf_key = pending["pdf_key"]
            st.session_state[pdf_key] = True
            st.session_state[f"po_pdf_data_{req['id']}"] = pdf_bytes
            st.session_state[f"po_pdf_filename_{req['id']}"] = f"PO_{po_ref or req['id']}.pdf"
            # Clear pending generation
            del st.session_state.pending_po_generation
            st.success("PO generated successfully. Download button will appear below.")
            st.rerun()
        except Exception as error:  # pragma: no cover - UI feedback
            st.error(str(error))
    
    if col2.button("Cancel", use_container_width=True, key=f"cancel_po_{req['id']}"):
        # Clear pending generation
        if "pending_po_generation" in st.session_state:
            del st.session_state.pending_po_generation
        st.rerun()


def render_receiving(db_path: str) -> None:
    """List PO-generated requests and allow marking as received."""
    st.subheader("PO Generated (Received / Download)")
    po_generated = safe_list_by_status(db_path, ["po_generated"])
    if not po_generated:
        st.info("No PO-generated requests awaiting receipt.")
        return

    # Header row (slightly wider Download/Action columns so labels don't wrap)
    header_cols = st.columns([1.5, 3, 2, 2, 3, 1.5, 1.5])
    header_cols[0].markdown("**Serial #**")
    header_cols[1].markdown("**Vehicle — Vendor**")
    header_cols[2].markdown("**Quantity**")
    header_cols[3].markdown("**Total Price**")
    header_cols[4].markdown("**PO Ref**")
    # Use custom download icon in header for clarity
    header_cols[5].image("assets/download_icon.png", width=20)
    header_cols[6].markdown("**Action**")
    st.divider()

    for req in po_generated:
        cols = st.columns([1.5, 3, 2, 2, 3, 1.5, 1.5])
        cols[0].markdown(f"**{req.get('serial_number', '—')}**")
        cols[1].markdown(f"**{req['plate_number']}** — {req.get('vendor_name') or '—'}")
        qty_text = "Full Tank" if req.get("unit") and req.get("unit").upper() == "FULLTANK" else f"{req['quantity']} liters"
        cols[2].write(qty_text)
        if req.get("total_price") and req.get("unit", "").upper() != "FULLTANK":
            cols[3].write(f"₱{req['total_price']:,.2f}")
        else:
            cols[3].write("—")
        cols[4].write(f"PO Ref: {req.get('po_reference') or '—'}")
        
        # Generate PDF only when download button is clicked (lazy loading)
        # Use session state to track which PDFs need to be generated
        pdf_key = f"po_pdf_{req['id']}"
        download_btn_key = f"dl_btn_{req['id']}"
        
        # Check if PDF is already generated and cached
        pdf_bytes = None
        if pdf_key in st.session_state and isinstance(st.session_state[pdf_key], bytes):
            pdf_bytes = st.session_state[pdf_key]
        
        # Check if download was requested (button clicked)
        if cols[5].button("Download", key=download_btn_key):
            # Generate PDF on demand
            try:
                pdf_bytes = safe_build_po_pdf(db_path, req)
                if pdf_bytes:
                    st.session_state[pdf_key] = pdf_bytes
                    st.session_state[f"{pdf_key}_filename"] = f"PO_{req.get('po_reference') or req['id']}.pdf"
                else:
                    st.error("Failed to generate PO PDF.")
            except Exception as error:
                st.error(f"Error generating PDF: {error}")
        
        # Show download button and icon if PDF is available
        if pdf_bytes:
            cols[5].image("assets/download_icon.png", width=24)
            cols[5].download_button(
                "Download",
                data=pdf_bytes,
                file_name=st.session_state.get(f"{pdf_key}_filename", f"PO_{req.get('po_reference') or req['id']}.pdf"),
                mime="application/pdf",
                key=f"po_dl_{req['id']}",
            )
        
        # Mark as received (actual_quantity will be captured in billing module)
        if cols[6].button("Received", key=f"recv_btn_{req['id']}", use_container_width=False):
            try:
                update_requisition_received(db_path, req["id"])
                st.success("Marked as received.")
                st.rerun()
            except Exception as error:  # pragma: no cover - UI feedback
                st.error(str(error))


def build_po_pdf(db_path: str, req: Dict[str, str], po_reference: str) -> bytes:
    """Build PO PDF bytes from requisition context."""
    from datetime import datetime
    from pathlib import Path

    unit_price = req.get("unit_price")
    total_price = req.get("total_price")

    # Use current date when generating PO (not requisition creation date)
    po_date = datetime.now().strftime("%B %d, %Y")

    # Get absolute paths for logos by vehicle company (xhtml2pdf requires absolute paths)
    assets_dir = Path("assets").resolve()
    company = (req.get("company") or "").strip().upper()
    if company == "DIC":
        logo_left = assets_dir / "dic_logo.png"
        logo_right = assets_dir / "eskina_logo.png"
        logo_mte_path = str(logo_left) if logo_left.exists() else ""
        logo_planters_path = str(logo_right) if logo_right.exists() else ""
    elif company == "DSRDC":
        logo_left = assets_dir / "DSRDC_logo.png"
        logo_mte_path = str(logo_left) if logo_left.exists() else ""
        logo_planters_path = ""
    else:
        # Default: no company or other — MTE left, Planters right
        logo_mte = assets_dir / "mte_logo.png"
        logo_planters = assets_dir / "planters_logo.png"
        logo_mte_path = str(logo_mte) if logo_mte.exists() else ""
        logo_planters_path = str(logo_planters) if logo_planters.exists() else ""

    qty_display = "Full Tank" if req.get("unit", "").upper() == "FULLTANK" else req.get("quantity") or ""
    unit_display = "LITERS"

    # Use requester's full name from Users table (fallback to stored requestor_name or username)
    requester_id = req.get("requester_id")
    requestor_full_name = ""
    if requester_id is not None:
        try:
            requestor_full_name = fetch_full_name_by_id(db_path, int(requester_id)) or ""
        except (TypeError, ValueError):
            pass
    if not requestor_full_name:
        requestor_full_name = req.get("requester_name") or req.get("requestor_name") or ""
    plate_number = req.get("plate_number") or ""
    remarks_value = f"FOR {requestor_full_name} WITH PLATE NO {plate_number}"

    context = {
        "po_reference": po_reference or req.get("po_reference") or "",
        "serial_number": req.get("serial_number") or "",
        "vendor_name": req.get("vendor_name") or "",
        "vendor_address": req.get("vendor_address") or "",
        "po_date": po_date,
        "quantity": qty_display,
        "unit": unit_display,
        "fuel_type": req.get("fuel_type") or "",
        "unit_price": f"₱ {(unit_price or 0):,.2f}",
        "total_price": f"₱ {(total_price or 0):,.2f}",
        "remarks": remarks_value,
        "notes": remarks_value,
        "requested_by": requestor_full_name,
        "approved_by": req.get("approved_by") or "",
        "logo_mte_path": logo_mte_path,
        "logo_planters_path": logo_planters_path,
    }
    html = render_purchase_order_html(context)
    return generate_purchase_order_pdf(context | {"html": html})


def safe_build_po_pdf(db_path: str, req: Dict[str, str]) -> Optional[bytes]:
    """Safely generate PO PDF bytes; return None on error."""
    try:
        return build_po_pdf(db_path, req, req.get("po_reference", ""))
    except Exception as error:  # pragma: no cover - UI feedback
        st.warning(f"Could not generate PO PDF: {error}")
        return None


@st.cache_data(ttl=60)  # Cache for 60 seconds to improve performance
def safe_list_by_status(db_path: str, statuses: List[str]) -> List[dict]:
    """Safely list requisitions by status with UI feedback."""
    try:
        return list_requisitions_by_status(db_path, statuses)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load requisitions: {error}")
        return []

