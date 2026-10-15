"""Fleet Registrations / Renewal service (LTO / OR-CR on vehicles)."""
from typing import Any, Dict, List, Optional

from src.audit import VEHICLE_REGISTRATION_AUDIT_FIELDS, log_field_update
from src.database import (
    REGISTRATION_DUE_SOON_DAYS,
    fetch_car_by_id,
    list_vehicle_registrations,
    update_vehicle_registration,
)


def get_registrations(db_path: str) -> List[Dict[str, Any]]:
    """Return active vehicles with registration alert fields."""
    return list_vehicle_registrations(db_path)


def get_registration_summary(db_path: str) -> Dict[str, Any]:
    """
    Build alert counts for the Registrations module header.

    Args:
        db_path: SQLite database path.

    Returns:
        Dict with total and per-status counts plus due_soon_days window.
    """
    rows = list_vehicle_registrations(db_path)
    counts = {"expired": 0, "due_soon": 0, "missing": 0, "current": 0}
    for row in rows:
        status = str(row.get("alert_status") or "missing")
        if status in counts:
            counts[status] += 1
    return {
        "total": len(rows),
        "due_soon_days": REGISTRATION_DUE_SOON_DAYS,
        **counts,
    }


def save_registration(
    db_path: str,
    car_id: int,
    lto_expiry: Optional[str] = None,
    registration_date: Optional[str] = None,
    or_number: Optional[str] = None,
    cr_number: Optional[str] = None,
    mv_file_no: Optional[str] = None,
    registration_remarks: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Update registration fields and return the refreshed list row.

    Raises:
        RuntimeError: If update fails or vehicle is not in the active company-owned list.
    """
    before = fetch_car_by_id(db_path, car_id)
    update_vehicle_registration(
        db_path,
        car_id,
        lto_expiry=lto_expiry,
        registration_date=registration_date,
        or_number=or_number,
        cr_number=cr_number,
        mv_file_no=mv_file_no,
        registration_remarks=registration_remarks,
    )
    after = fetch_car_by_id(db_path, car_id)
    log_field_update(
        db_path,
        "vehicle",
        car_id,
        "registration_updated",
        actor,
        before,
        after,
        VEHICLE_REGISTRATION_AUDIT_FIELDS,
    )
    rows = list_vehicle_registrations(db_path)
    match = next((row for row in rows if int(row["id"]) == car_id), None)
    if not match:
        raise RuntimeError("Registration saved but vehicle not found in active list.")
    return match
