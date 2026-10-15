"""Service center master data service."""
from typing import Any, Dict, List, Optional

from src.audit import SERVICE_CENTER_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    create_service_center,
    fetch_service_center_by_id,
    list_service_centers,
    reactivate_service_center,
    soft_delete_service_center,
    update_service_center,
)


def get_all_service_centers(db_path: str) -> List[Dict[str, Any]]:
    """Return every service center, including inactive ones, for Master Data."""
    return list_service_centers(db_path, active_only=False)


def add_service_center(
    db_path: str,
    name: str,
    address: str,
    contact_no: str,
    actor: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a service center and write an audit row."""
    service_center_id = create_service_center(db_path, name, address, contact_no)
    created = fetch_service_center_by_id(db_path, service_center_id)
    log_audit(
        db_path,
        "service_center",
        service_center_id,
        "created",
        actor,
        new_values=pick_fields(created, SERVICE_CENTER_AUDIT_FIELDS),
    )
    return service_center_id


def save_service_center(
    db_path: str,
    service_center_id: int,
    name: str,
    address: str,
    contact_no: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update name, address, and contact number."""
    before = fetch_service_center_by_id(db_path, service_center_id)
    update_service_center(db_path, service_center_id, name, address, contact_no)
    after = fetch_service_center_by_id(db_path, service_center_id)
    log_field_update(
        db_path,
        "service_center",
        service_center_id,
        "updated",
        actor,
        before,
        after,
        SERVICE_CENTER_AUDIT_FIELDS,
    )


def deactivate_service_center(
    db_path: str,
    service_center_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Soft-delete a service center."""
    before = fetch_service_center_by_id(db_path, service_center_id)
    soft_delete_service_center(db_path, service_center_id)
    after = fetch_service_center_by_id(db_path, service_center_id)
    log_field_update(
        db_path,
        "service_center",
        service_center_id,
        "deactivated",
        actor,
        before,
        after,
        ["is_active"],
    )


def restore_service_center(
    db_path: str,
    service_center_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Reactivate a service center."""
    before = fetch_service_center_by_id(db_path, service_center_id)
    reactivate_service_center(db_path, service_center_id)
    after = fetch_service_center_by_id(db_path, service_center_id)
    log_field_update(
        db_path,
        "service_center",
        service_center_id,
        "reactivated",
        actor,
        before,
        after,
        ["is_active"],
    )
