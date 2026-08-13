"""Audit trail helpers — append-only change logging."""
import json
from typing import Any, Dict, List, Optional, Tuple

from src.database import insert_audit_log

REQUISITION_AUDIT_FIELDS = [
    "serial_number",
    "status",
    "quantity",
    "unit",
    "fuel_type",
    "requestor_name",
    "vehicle_id",
    "vendor_id",
    "unit_price",
    "total_price",
    "po_reference",
    "prepared_by",
    "po_signatory",
    "actual_quantity",
    "actual_unit_price",
    "receipt_number",
    "received_date",
    "invoice_number",
    "notes",
    "cancel_reason",
    "cancelled_by",
    "released_date",
    "released_by",
    "release_remarks",
    "receiving_remarks",
    "settlement_type",
    "cc_card_reference",
    "cc_statement_reference",
    "cc_reconcile_report_no",
    "cc_reconciled_at",
    "cc_reconciled_by",
]

VEHICLE_AUDIT_FIELDS = [
    "plate_number",
    "model",
    "fuel_type",
    "company",
    "vendor_id",
    "assigned_to",
    "is_active",
]

VENDOR_AUDIT_FIELDS = ["name", "address", "is_active"]

COMPANY_AUDIT_FIELDS = ["code", "name", "is_active"]

USER_AUDIT_FIELDS = ["username", "full_name", "role", "email", "company", "is_active"]


def actor_from_user(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a stable actor dict from an authenticated user record.

    Args:
        user: User dict from session (id, username, role, full_name).

    Returns:
        Actor metadata for audit rows.
    """
    if not user:
        return {
            "actor_user_id": None,
            "actor_username": "system",
            "actor_role": "",
            "actor_name": "System",
        }
    return {
        "actor_user_id": user.get("id"),
        "actor_username": user.get("username") or "",
        "actor_role": user.get("role") or "",
        "actor_name": (user.get("full_name") or user.get("username") or "").strip(),
    }


def pick_fields(data: Optional[Dict[str, Any]], keys: List[str]) -> Dict[str, Any]:
    """Return a subset of dict keys for audit snapshots."""
    if not data:
        return {}
    return {key: data.get(key) for key in keys if key in data}


def diff_snapshots(
    old: Dict[str, Any],
    new: Dict[str, Any],
    keys: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Compare two snapshots and return only changed fields.

    Args:
        old: Previous values.
        new: New values.
        keys: Optional field list; defaults to union of keys.

    Returns:
        Tuple of (old_changes, new_changes).
    """
    field_keys = keys or sorted(set(old.keys()) | set(new.keys()))
    old_out: Dict[str, Any] = {}
    new_out: Dict[str, Any] = {}
    for key in field_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            old_out[key] = old_val
            new_out[key] = new_val
    return old_out, new_out


def log_audit(
    db_path: str,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: Optional[Dict[str, Any]],
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one immutable audit log row.

    Args:
        db_path: SQLite database path.
        entity_type: Entity category (requisition, vehicle, vendor, user, fuel_price).
        entity_id: Primary key of the entity.
        action: Action verb (created, updated, approved, etc.).
        actor: Authenticated user dict or None for system.
        old_values: Previous field values (JSON-serializable).
        new_values: New field values (JSON-serializable).
        metadata: Extra context (serial numbers, batch ids, etc.).
    """
    actor_info = actor_from_user(actor)
    insert_audit_log(
        db_path,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_info["actor_user_id"],
        actor_username=actor_info["actor_username"],
        actor_role=actor_info["actor_role"],
        actor_name=actor_info["actor_name"],
        old_values_json=json.dumps(old_values or {}, default=str),
        new_values_json=json.dumps(new_values or {}, default=str),
        metadata_json=json.dumps(metadata or {}, default=str),
    )


def log_field_update(
    db_path: str,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: Optional[Dict[str, Any]],
    before: Optional[Dict[str, Any]],
    after: Optional[Dict[str, Any]],
    fields: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an update using only fields that changed."""
    old_vals, new_vals = diff_snapshots(
        pick_fields(before, fields),
        pick_fields(after, fields),
        fields,
    )
    if not old_vals and not new_vals and action != "created":
        return
    log_audit(
        db_path,
        entity_type,
        entity_id,
        action,
        actor,
        old_values=old_vals or None,
        new_values=new_vals or None,
        metadata=metadata,
    )
