"""Vehicle master data service."""
from typing import Any, Dict, List, Optional

from src.audit import VEHICLE_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    assert_company_assignable,
    fetch_car_by_id,
    list_cars,
    soft_delete_car,
    update_car,
    upsert_car,
)
from src.utils.plate import normalize_plate_number


def get_active_vehicles(db_path: str) -> List[Dict[str, Any]]:
    """Return all active vehicles with vendor names."""
    return list_cars(db_path)


def create_vehicle(
    db_path: str,
    plate_number: str,
    model: str,
    fuel_type: str,
    company: str,
    assigned_to: str,
    vendor_id: Optional[int] = None,
    registration_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
    is_company_owned: bool = False,
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create or reactivate a vehicle by plate number."""
    company_code = assert_company_assignable(db_path, company)
    try:
        plate = normalize_plate_number(plate_number)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    car_id = upsert_car(
        db_path,
        plate,
        model.strip(),
        vendor_id,
        fuel_type,
        company_code,
        assigned_to.strip(),
        registration_date=registration_date,
        expiration_date=expiration_date,
        is_company_owned=is_company_owned,
    )
    created = fetch_car_by_id(db_path, car_id)
    log_audit(
        db_path,
        "vehicle",
        car_id,
        "created",
        actor,
        new_values=pick_fields(created, VEHICLE_AUDIT_FIELDS),
    )
    return car_id


def save_vehicle(
    db_path: str,
    car_id: int,
    plate_number: str,
    model: str,
    fuel_type: str,
    company: str,
    assigned_to: str,
    vendor_id: Optional[int] = None,
    registration_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
    is_company_owned: bool = False,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update an existing vehicle."""
    before = fetch_car_by_id(db_path, car_id)
    previous_company = (before or {}).get("company")
    company_code = assert_company_assignable(
        db_path, company, previous_code=previous_company
    )
    try:
        plate = normalize_plate_number(plate_number)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    update_car(
        db_path,
        car_id,
        plate,
        model.strip(),
        vendor_id,
        fuel_type,
        company_code,
        assigned_to.strip(),
        registration_date=registration_date,
        expiration_date=expiration_date,
        is_company_owned=is_company_owned,
    )
    after = fetch_car_by_id(db_path, car_id)
    log_field_update(
        db_path,
        "vehicle",
        car_id,
        "updated",
        actor,
        before,
        after,
        VEHICLE_AUDIT_FIELDS,
    )


def deactivate_vehicle(
    db_path: str,
    car_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Soft-delete a vehicle."""
    before = fetch_car_by_id(db_path, car_id)
    soft_delete_car(db_path, car_id)
    after = fetch_car_by_id(db_path, car_id)
    log_field_update(
        db_path,
        "vehicle",
        car_id,
        "deactivated",
        actor,
        before,
        after,
        ["is_active"],
    )
