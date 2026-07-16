"""Requisition and request workflow services."""
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    can_user_edit_requisition,
    check_prior_approved_requests,
    create_requisition,
    fetch_requisition_by_id,
    fetch_requisition_record,
    list_cars,
    list_requisitions_for_user,
    list_vendors,
    update_requisition,
)


def _unit_from_mode(quantity_mode: str) -> str:
    """Map API quantity mode to database unit value."""
    return "FULLTANK" if quantity_mode == "fulltank" else "liters"


def get_form_context(db_path: str, user_id: int) -> Dict[str, Any]:
    """Build vehicles/vendors for the request form."""
    return {
        "vehicles": list_cars(db_path),
        "vendors": list_vendors(db_path),
    }


def list_user_requisitions(
    db_path: str,
    user_id: int,
    user_role: str,
) -> List[Dict[str, Any]]:
    """List requisitions for the current user with edit eligibility."""
    role = (user_role or "").lower()
    rows = list_requisitions_for_user(db_path, user_id)
    result: List[Dict[str, Any]] = []
    for row in rows:
        can_edit, edit_error = can_user_edit_requisition(
            db_path, row["id"], user_id, role
        )
        enriched = dict(row)
        enriched["is_edited"] = bool(row.get("is_edited"))
        enriched["can_edit"] = can_edit
        enriched["edit_error"] = edit_error
        result.append(enriched)
    return result


def get_requisition(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str,
) -> Optional[Dict[str, Any]]:
    """Fetch one requisition if the user owns it or may edit it."""
    row = fetch_requisition_by_id(db_path, requisition_id)
    if not row:
        return None

    is_owner = row.get("requester_id") == user_id
    role = (user_role or "").lower()
    can_edit, edit_error = can_user_edit_requisition(
        db_path, requisition_id, user_id, role
    )
    if not is_owner and not can_edit:
        return None

    enriched = dict(row)
    enriched["is_edited"] = bool(row.get("is_edited"))
    enriched["can_edit"] = can_edit
    enriched["edit_error"] = edit_error
    return enriched


def submit_requisition(
    db_path: str,
    requester_id: int,
    vehicle_id: int,
    vendor_id: int,
    fuel_type: str,
    quantity_mode: str,
    quantity: float,
    notes: str,
    requestor_name: str,
    settlement_type: str = "vendor_invoice",
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a new pending requisition."""
    unit = _unit_from_mode(quantity_mode)
    if quantity_mode == "numeric":
        if quantity <= 0:
            raise RuntimeError("Positive quantity is required for numeric mode.")
        if quantity != int(quantity):
            raise RuntimeError("Quantity must be a whole number of liters.")
        quantity = float(int(quantity))
    if quantity_mode == "fulltank":
        quantity = 0.0

    req_id = create_requisition(
        db_path=db_path,
        requester_id=requester_id,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        quantity=quantity,
        unit=unit,
        unit_price=None,
        notes=notes.strip(),
        fuel_type=fuel_type,
        requestor_name=requestor_name.strip(),
        settlement_type=settlement_type,
    )
    created = fetch_requisition_record(db_path, req_id)
    log_audit(
        db_path,
        "requisition",
        req_id,
        "created",
        actor,
        new_values=pick_fields(created, REQUISITION_AUDIT_FIELDS),
    )
    return req_id


def save_requisition(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str,
    vehicle_id: int,
    vendor_id: int,
    fuel_type: str,
    quantity_mode: str,
    quantity: float,
    notes: str,
    settlement_type: str = "vendor_invoice",
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update a pending requisition."""
    before = fetch_requisition_record(db_path, requisition_id)
    unit = _unit_from_mode(quantity_mode)
    if quantity_mode == "numeric":
        if quantity <= 0:
            raise RuntimeError("Positive quantity is required for numeric mode.")
        if quantity != int(quantity):
            raise RuntimeError("Quantity must be a whole number of liters.")
        quantity = float(int(quantity))
    if quantity_mode == "fulltank":
        quantity = 0.0

    update_requisition(
        db_path=db_path,
        requisition_id=requisition_id,
        user_id=user_id,
        user_role=(user_role or "").lower(),
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        quantity=quantity,
        unit=unit,
        unit_price=None,
        notes=notes.strip(),
        fuel_type=fuel_type,
        settlement_type=settlement_type,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "updated",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )


def get_prior_approved(db_path: str, vehicle_id: int, days: int = 2) -> List[Dict[str, Any]]:
    """Return prior approved requisitions for a vehicle within N days."""
    return check_prior_approved_requests(db_path, vehicle_id, days=days)
