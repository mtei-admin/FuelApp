"""Approval workflow services."""
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    cancel_approved_requisition,
    fetch_requisition_by_id,
    fetch_requisition_record,
    get_vendor_fuel_price_for_fuel_type,
    list_pending_requisitions,
    list_requisitions_by_status,
    list_vehicle_requisition_history,
    update_requisition,
    update_requisition_status,
)


def _compute_display_total(db_path: str, req: Dict[str, Any]) -> Optional[float]:
    """Compute quantity × latest vendor fuel price for approvals display."""
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


def list_pending(
    db_path: str,
    user_role: str,
) -> List[Dict[str, Any]]:
    """List pending requisitions with display totals and permission flags."""
    can_approve = user_role.lower() in {"approver", "accounting", "superuser"}
    rows = list_pending_requisitions(db_path)
    result: List[Dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        enriched["is_edited"] = bool(row.get("is_edited"))
        enriched["can_edit"] = False
        enriched["display_total"] = _compute_display_total(db_path, row)
        enriched["can_approve"] = can_approve
        result.append(enriched)
    return result


def pending_count(db_path: str) -> int:
    """Return count of pending requisitions for sidebar badge."""
    return len(list_pending_requisitions(db_path))


def list_vehicle_history(
    db_path: str, vehicle_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Return recent requisitions for a vehicle (approval context)."""
    return list_vehicle_requisition_history(db_path, vehicle_id, limit=limit)


def list_approved_awaiting_po(db_path: str) -> List[Dict[str, Any]]:
    """List approved requisitions not yet converted to PO."""
    return list_requisitions_by_status(db_path, ["approved"])


def cancel_approved(
    db_path: str,
    requisition_id: int,
    cancelled_by_user_id: int,
    reason: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Cancel an approved requisition before PO generation."""
    before = fetch_requisition_record(db_path, requisition_id)
    cancel_approved_requisition(db_path, requisition_id, cancelled_by_user_id, reason)
    after = fetch_requisition_record(db_path, requisition_id)
    log_audit(
        db_path,
        "requisition",
        requisition_id,
        "cancelled",
        actor,
        old_values=pick_fields(before, ["status"]),
        new_values=pick_fields(
            after, ["status", "cancel_reason", "cancelled_by", "approved_by"]
        ),
        metadata={
            "serial_number": after.get("serial_number"),
            "cancel_reason": after.get("cancel_reason"),
        },
    )


def approve_requisition(
    db_path: str,
    requisition_id: int,
    approver_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Mark requisition as approved."""
    before = fetch_requisition_record(db_path, requisition_id)
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req or req.get("status") != "pending":
        raise RuntimeError("Requisition not found or not pending.")
    update_requisition_status(db_path, requisition_id, "approved", approver_id)
    after = fetch_requisition_record(db_path, requisition_id)
    log_audit(
        db_path,
        "requisition",
        requisition_id,
        "approved",
        actor,
        old_values=pick_fields(before, ["status"]),
        new_values=pick_fields(after, ["status", "approved_by"]),
        metadata={"serial_number": after.get("serial_number")},
    )


def reject_requisition(
    db_path: str,
    requisition_id: int,
    approver_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Mark requisition as rejected."""
    before = fetch_requisition_record(db_path, requisition_id)
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req or req.get("status") != "pending":
        raise RuntimeError("Requisition not found or not pending.")
    update_requisition_status(db_path, requisition_id, "rejected", approver_id)
    after = fetch_requisition_record(db_path, requisition_id)
    log_audit(
        db_path,
        "requisition",
        requisition_id,
        "rejected",
        actor,
        old_values=pick_fields(before, ["status"]),
        new_values=pick_fields(after, ["status"]),
        metadata={"serial_number": after.get("serial_number")},
    )


def update_pending_quantity(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str,
    quantity_mode: str,
    quantity: float,
    notes: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Allow approver to edit quantity on a pending requisition."""
    before = fetch_requisition_record(db_path, requisition_id)
    full_req = fetch_requisition_by_id(db_path, requisition_id)
    if not full_req or full_req.get("status") != "pending":
        raise RuntimeError("Requisition not found or not pending.")

    unit = "FULLTANK" if quantity_mode == "fulltank" else "liters"
    if quantity_mode == "numeric" and quantity <= 0:
        raise RuntimeError("Positive quantity is required for numeric mode.")
    if quantity_mode == "fulltank":
        quantity = 0.0

    update_requisition(
        db_path=db_path,
        requisition_id=requisition_id,
        user_id=user_id,
        user_role=user_role,
        vehicle_id=full_req["vehicle_id"],
        vendor_id=full_req.get("vendor_id"),
        quantity=quantity,
        unit=unit,
        unit_price=full_req.get("unit_price"),
        notes=notes.strip(),
        fuel_type=full_req.get("fuel_type"),
    )
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "approval_edit",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )
