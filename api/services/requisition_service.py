"""Requisition and request workflow services."""
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    admin_cancel_requisition,
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


def _resolve_unit_price(_user: Dict[str, Any], unit_price: Optional[float]) -> Optional[float]:
    """
    Normalize optional unit price from a request create/update payload.

    Any user who can submit or edit a request may set or clear unit price.
    """
    if unit_price is None:
        return None
    if unit_price <= 0:
        return None
    return float(unit_price)


def get_form_context(db_path: str, user_id: int) -> Dict[str, Any]:
    """Build vehicles/vendors for the request form."""
    return {
        "vehicles": list_cars(db_path),
        "vendors": list_vendors(db_path),
    }


def list_user_requisitions(
    db_path: str,
    user_id: int,
    user: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """List requisitions for the current user with edit eligibility."""
    rows = list_requisitions_for_user(db_path, user_id)
    result: List[Dict[str, Any]] = []
    for row in rows:
        can_edit, edit_error = can_user_edit_requisition(
            db_path, row["id"], user_id, user.get("role", ""), user=user
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
    user: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Fetch one requisition if the user owns it or may edit it."""
    row = fetch_requisition_by_id(db_path, requisition_id)
    if not row:
        return None

    is_owner = row.get("requester_id") == user_id
    can_edit, edit_error = can_user_edit_requisition(
        db_path, requisition_id, user_id, user.get("role", ""), user=user
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
    unit_price: Optional[float] = None,
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

    resolved_price = _resolve_unit_price(actor or {}, unit_price)

    req_id = create_requisition(
        db_path=db_path,
        requester_id=requester_id,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        quantity=quantity,
        unit=unit,
        unit_price=resolved_price,
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
    user: Dict[str, Any],
    vehicle_id: int,
    vendor_id: int,
    fuel_type: str,
    quantity_mode: str,
    quantity: float,
    notes: str,
    settlement_type: str = "vendor_invoice",
    actor: Optional[Dict[str, Any]] = None,
    unit_price: Optional[float] = None,
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

    resolved_price = _resolve_unit_price(user, unit_price)
    if unit_price is None:
        resolved_price = before.get("unit_price")

    update_requisition(
        db_path=db_path,
        requisition_id=requisition_id,
        user_id=user_id,
        user_role=(user.get("role") or "").lower(),
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        quantity=quantity,
        unit=unit,
        unit_price=resolved_price,
        notes=notes.strip(),
        fuel_type=fuel_type,
        settlement_type=settlement_type,
        user=user,
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


def admin_cancel(
    db_path: str,
    requisition_id: int,
    cancelled_by_user_id: int,
    reason: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Superuser cancel for pending through received.

    Keeps PO number, PO date, and receipt fields when present.
    """
    before = fetch_requisition_record(db_path, requisition_id)
    admin_cancel_requisition(db_path, requisition_id, cancelled_by_user_id, reason)
    after = fetch_requisition_record(db_path, requisition_id)
    log_audit(
        db_path,
        "requisition",
        requisition_id,
        "cancelled",
        actor,
        old_values=pick_fields(before, ["status", "po_reference", "po_created_at"]),
        new_values=pick_fields(
            after, ["status", "cancel_reason", "cancelled_by", "po_reference"]
        ),
        metadata={
            "serial_number": after.get("serial_number"),
            "cancel_reason": after.get("cancel_reason"),
            "admin_cancel": True,
        },
    )
