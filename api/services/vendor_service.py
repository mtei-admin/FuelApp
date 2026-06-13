"""Vendor master data service."""
from typing import Any, Dict, List

from src.database import (
    list_vendors,
    soft_delete_vendor,
    update_vendor,
    upsert_vendor,
)


def get_active_vendors(db_path: str) -> List[Dict[str, Any]]:
    """Return all active vendors."""
    return list_vendors(db_path)


def create_vendor(db_path: str, name: str, address: str = "") -> int:
    """Create or reactivate a vendor by name."""
    return upsert_vendor(db_path, name.strip(), address.strip())


def save_vendor(
    db_path: str,
    vendor_id: int,
    name: str,
    address: str = "",
) -> None:
    """Update an existing vendor."""
    update_vendor(db_path, vendor_id, name.strip(), address.strip())


def deactivate_vendor(db_path: str, vendor_id: int) -> None:
    """Soft-delete a vendor."""
    soft_delete_vendor(db_path, vendor_id)
