"""Vendor master data service."""
from typing import Any, Dict, List, Optional

from src.audit import VENDOR_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    fetch_vendor_by_id,
    list_vendors,
    soft_delete_vendor,
    update_vendor,
    upsert_vendor,
)


def get_active_vendors(db_path: str) -> List[Dict[str, Any]]:
    """Return all active vendors."""
    return list_vendors(db_path)


def create_vendor(
    db_path: str,
    name: str,
    address: str = "",
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create or reactivate a vendor by name."""
    vendor_id = upsert_vendor(db_path, name.strip(), address.strip())
    created = fetch_vendor_by_id(db_path, vendor_id)
    log_audit(
        db_path,
        "vendor",
        vendor_id,
        "created",
        actor,
        new_values=pick_fields(created, VENDOR_AUDIT_FIELDS),
    )
    return vendor_id


def save_vendor(
    db_path: str,
    vendor_id: int,
    name: str,
    address: str = "",
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update an existing vendor."""
    before = fetch_vendor_by_id(db_path, vendor_id)
    update_vendor(db_path, vendor_id, name.strip(), address.strip())
    after = fetch_vendor_by_id(db_path, vendor_id)
    log_field_update(
        db_path,
        "vendor",
        vendor_id,
        "updated",
        actor,
        before,
        after,
        VENDOR_AUDIT_FIELDS,
    )


def deactivate_vendor(
    db_path: str,
    vendor_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Soft-delete a vendor."""
    before = fetch_vendor_by_id(db_path, vendor_id)
    soft_delete_vendor(db_path, vendor_id)
    after = fetch_vendor_by_id(db_path, vendor_id)
    log_field_update(
        db_path,
        "vendor",
        vendor_id,
        "deactivated",
        actor,
        before,
        after,
        ["is_active"],
    )
