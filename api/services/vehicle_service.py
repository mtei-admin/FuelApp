"""Vehicle master data service."""
from typing import Any, Dict, List, Optional

from src.database import list_cars, soft_delete_car, update_car, upsert_car


def get_active_vehicles(db_path: str) -> List[Dict[str, Any]]:
    """Return all active vehicles with vendor names."""
    return list_cars(db_path)


def create_vehicle(
    db_path: str,
    plate_number: str,
    model: str,
    fuel_type: str,
    company: str,
    vendor_id: Optional[int] = None,
    driver_name: Optional[str] = None,
) -> int:
    """Create or reactivate a vehicle by plate number."""
    return upsert_car(
        db_path,
        plate_number.strip(),
        model.strip(),
        vendor_id,
        fuel_type,
        company,
        driver_name,
    )


def save_vehicle(
    db_path: str,
    car_id: int,
    plate_number: str,
    model: str,
    fuel_type: str,
    company: str,
    vendor_id: Optional[int] = None,
    driver_name: Optional[str] = None,
) -> None:
    """Update an existing vehicle."""
    update_car(
        db_path,
        car_id,
        plate_number.strip(),
        model.strip(),
        vendor_id,
        fuel_type,
        company,
    )


def deactivate_vehicle(db_path: str, car_id: int) -> None:
    """Soft-delete a vehicle."""
    soft_delete_car(db_path, car_id)
