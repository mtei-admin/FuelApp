"""Approval workflow services."""
from typing import Any, Dict, List, Optional

from src.database import (
    fetch_requisition_by_id,
    get_vendor_fuel_price_for_fuel_type,
    list_pending_requisitions,
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


def approve_requisition(
    db_path: str,
    requisition_id: int,
    approver_id: int,
) -> None:
    """Mark requisition as approved."""
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req or req.get("status") != "pending":
        raise RuntimeError("Requisition not found or not pending.")
    update_requisition_status(db_path, requisition_id, "approved", approver_id)


def reject_requisition(db_path: str, requisition_id: int, approver_id: int) -> None:
    """Mark requisition as rejected."""
    req = fetch_requisition_by_id(db_path, requisition_id)
    if not req or req.get("status") != "pending":
        raise RuntimeError("Requisition not found or not pending.")
    update_requisition_status(db_path, requisition_id, "rejected", approver_id)


def update_pending_quantity(
    db_path: str,
    requisition_id: int,
    user_id: int,
    user_role: str,
    quantity_mode: str,
    quantity: float,
    notes: str,
) -> None:
    """Allow approver to edit quantity on a pending requisition."""
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
