"""PMS due dates and work orders."""
from typing import Any, Dict, List, Optional

from src.audit import (
    PMS_SCHEDULE_AUDIT_FIELDS,
    PMS_WORK_ORDER_AUDIT_FIELDS,
    log_audit,
    log_field_update,
    pick_fields,
)
from src.database import (
    PMS_DUE_SOON_DAYS,
    cancel_pms_work_order,
    complete_pms_work_order,
    fetch_work_order,
    list_pms_vehicles,
    list_pms_work_order_history,
    open_pms_work_order,
    update_pms_schedule,
    update_pms_work_order,
)


def _header_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Copy write-request fields the database layer understands."""
    return {
        "transaction_no": payload.get("transaction_no"),
        "doc_date": payload.get("doc_date"),
        "repair_type": payload.get("repair_type"),
        "service_advisor": payload.get("service_advisor"),
        "technician": payload.get("technician"),
        "terms": payload.get("terms"),
        "shop_name": payload.get("shop_name"),
        "remarks": payload.get("remarks"),
        "current_odometer": payload.get("current_odometer"),
    }


def _line_dicts(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Copy line fields the database layer understands."""
    return [
        {
            "part_code": line.get("part_code"),
            "line_type": line.get("line_type"),
            "description": line.get("description"),
            "unit": line.get("unit"),
            "quantity": line.get("quantity"),
            "unit_price": line.get("unit_price"),
            "discount": line.get("discount"),
        }
        for line in lines
    ]


def get_pms_vehicles(db_path: str) -> List[Dict[str, Any]]:
    """Return active company-owned vehicles with PMS due status."""
    return list_pms_vehicles(db_path)


def get_pms_summary(db_path: str) -> Dict[str, Any]:
    """
    Build due-status counts and the number of open PMS jobs.

    Args:
        db_path: SQLite database path.

    Returns:
        Dict with total, per-status counts, open_jobs, and due_soon_days.
    """
    rows = list_pms_vehicles(db_path)
    counts = {"overdue": 0, "due_soon": 0, "missing": 0, "current": 0}
    open_jobs = 0
    for row in rows:
        status = str(row.get("alert_status") or "missing")
        if status in counts:
            counts[status] += 1
        if row.get("open_work_order_id"):
            open_jobs += 1
    return {
        "total": len(rows),
        "open_jobs": open_jobs,
        "due_soon_days": PMS_DUE_SOON_DAYS,
        **counts,
    }


def save_pms_schedule(
    db_path: str,
    vehicle_id: int,
    interval_months: Optional[int],
    next_due_date: Optional[str],
    interval_km: Optional[int] = None,
    last_odometer_km: Optional[int] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Update the date and odometer schedule and return the refreshed vehicle row.

    Raises:
        RuntimeError: If the vehicle is not tracked or the save cannot be reloaded.
    """
    before, after = update_pms_schedule(
        db_path,
        vehicle_id,
        interval_months,
        next_due_date,
        interval_km,
        last_odometer_km,
    )
    log_field_update(
        db_path,
        "pms_schedule",
        vehicle_id,
        "schedule_updated",
        actor,
        before,
        after,
        PMS_SCHEDULE_AUDIT_FIELDS,
    )
    return _vehicle_row(db_path, vehicle_id)


def get_pms_job(db_path: str, work_order_id: int) -> Dict[str, Any]:
    """Return one work order with lines."""
    row = fetch_work_order(db_path, work_order_id)
    if not row:
        raise RuntimeError(f"Work order {work_order_id} not found.")
    return row


def open_pms_job(
    db_path: str,
    payload: Dict[str, Any],
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Open a PMS work order and write an audit row."""
    created = open_pms_work_order(
        db_path,
        int(payload["vehicle_id"]),
        _header_dict(payload),
        _line_dicts(payload.get("lines") or []),
    )
    _audit_job(db_path, created, "opened", actor)
    return created


def save_pms_job(
    db_path: str,
    work_order_id: int,
    payload: Dict[str, Any],
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update an open PMS job and write an audit row."""
    updated = update_pms_work_order(
        db_path,
        work_order_id,
        _header_dict(payload),
        _line_dicts(payload.get("lines") or []),
    )
    _audit_job(db_path, updated, "updated", actor)
    return updated


def complete_pms_job(
    db_path: str,
    work_order_id: int,
    payload: Dict[str, Any],
    completed_by_user_id: Optional[int],
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Complete an open PMS job, roll the next due date, and audit both changes."""
    result = complete_pms_work_order(
        db_path,
        work_order_id,
        _header_dict(payload),
        _line_dicts(payload.get("lines") or []),
        completed_by_user_id,
    )
    work_order = result["work_order"]
    _audit_job(db_path, work_order, "completed", actor)
    log_field_update(
        db_path,
        "pms_schedule",
        int(work_order["vehicle_id"]),
        "schedule_updated",
        actor,
        result["schedule_before"],
        result["schedule_after"],
        PMS_SCHEDULE_AUDIT_FIELDS,
        metadata={"work_order_id": work_order["id"], "reason": "completed"},
    )
    return work_order


def cancel_pms_job(
    db_path: str,
    work_order_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Cancel an open PMS job without moving the due date or odometer chain."""
    cancelled = cancel_pms_work_order(db_path, work_order_id)
    _audit_job(db_path, cancelled, "cancelled", actor)
    return cancelled


def get_pms_history(db_path: str, vehicle_id: int) -> List[Dict[str, Any]]:
    """Return completed and cancelled PMS jobs for one vehicle."""
    return list_pms_work_order_history(db_path, vehicle_id)


def _audit_job(
    db_path: str,
    work_order: Dict[str, Any],
    action: str,
    actor: Optional[Dict[str, Any]],
) -> None:
    """Append an audit row for a PMS job header."""
    log_audit(
        db_path,
        "work_order",
        int(work_order["id"]),
        action,
        actor,
        new_values=pick_fields(work_order, PMS_WORK_ORDER_AUDIT_FIELDS),
        metadata={
            "vehicle_id": work_order.get("vehicle_id"),
            "plate_number": work_order.get("plate_number"),
            "line_count": len(work_order.get("lines") or []),
        },
    )


def _vehicle_row(db_path: str, vehicle_id: int) -> Dict[str, Any]:
    """Reload one vehicle from the PMS list."""
    rows = list_pms_vehicles(db_path)
    match = next((row for row in rows if int(row["id"]) == vehicle_id), None)
    if not match:
        raise RuntimeError("PMS schedule saved but vehicle not found in the active list.")
    return match
