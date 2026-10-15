"""Audit log query service with human-readable entity labels."""
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from src.database import get_connection, list_audit_log

EntityKey = Tuple[str, int]


def get_audit_entries(
    db_path: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
    q: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return audit log rows newest first with entity_label populated."""
    rows = list_audit_log(db_path, entity_type, entity_id, limit, q=q)
    labels = _resolve_entity_labels(db_path, rows)
    for row in rows:
        key = (row["entity_type"], row["entity_id"])
        row["entity_label"] = labels.get(key) or _label_from_row_snapshots(row)
    return rows


def _label_from_row_snapshots(row: Dict[str, Any]) -> Optional[str]:
    """Derive a display label from JSON snapshots when the entity row is gone."""
    entity_type = row.get("entity_type") or ""
    for source in (row.get("metadata"), row.get("new_values"), row.get("old_values")):
        if not source:
            continue
        if entity_type == "requisition" and source.get("serial_number"):
            return str(source["serial_number"])
        if entity_type in ("vendor", "fuel_price") and source.get("vendor_name"):
            return str(source["vendor_name"])
        if entity_type == "vehicle" and source.get("plate_number"):
            return str(source["plate_number"])
        if entity_type == "user" and source.get("username"):
            return str(source["username"])
        if entity_type == "service_center" and source.get("name"):
            return str(source["name"])
    return None


def _resolve_entity_labels(
    db_path: str,
    rows: List[Dict[str, Any]],
) -> Dict[EntityKey, str]:
    """Batch-load readable labels for audit log entities."""
    ids_by_type: Dict[str, Set[int]] = defaultdict(set)
    for row in rows:
        entity_type = row.get("entity_type") or ""
        entity_id = row.get("entity_id")
        if entity_id is None:
            continue
        ids_by_type[entity_type].add(int(entity_id))

    labels: Dict[EntityKey, str] = {}
    if not ids_by_type:
        return labels

    try:
        with get_connection(db_path) as connection:
            user_ids = ids_by_type.get("user", set())
            if user_ids:
                placeholders = ",".join("?" for _ in user_ids)
                cursor = connection.execute(
                    f"SELECT id, username FROM users WHERE id IN ({placeholders})",
                    list(user_ids),
                )
                for row in cursor.fetchall():
                    labels[("user", int(row[0]))] = row[1] or f"user-{row[0]}"

            req_ids = ids_by_type.get("requisition", set())
            if req_ids:
                placeholders = ",".join("?" for _ in req_ids)
                cursor = connection.execute(
                    f"""
                    SELECT id, serial_number
                    FROM requisitions
                    WHERE id IN ({placeholders})
                    """,
                    list(req_ids),
                )
                for row in cursor.fetchall():
                    serial = (row[1] or "").strip()
                    labels[("requisition", int(row[0]))] = serial or f"#{row[0]}"

            vehicle_ids = ids_by_type.get("vehicle", set())
            if vehicle_ids:
                placeholders = ",".join("?" for _ in vehicle_ids)
                cursor = connection.execute(
                    f"SELECT id, plate_number FROM cars WHERE id IN ({placeholders})",
                    list(vehicle_ids),
                )
                for row in cursor.fetchall():
                    plate = (row[1] or "").strip()
                    labels[("vehicle", int(row[0]))] = plate or f"vehicle-{row[0]}"

            vendor_ids = ids_by_type.get("vendor", set()) | ids_by_type.get("fuel_price", set())
            if vendor_ids:
                placeholders = ",".join("?" for _ in vendor_ids)
                cursor = connection.execute(
                    f"SELECT id, name FROM vendors WHERE id IN ({placeholders})",
                    list(vendor_ids),
                )
                vendor_names: Dict[int, str] = {}
                for row in cursor.fetchall():
                    name = (row[1] or "").strip()
                    vendor_names[int(row[0])] = name or f"vendor-{row[0]}"
                for vendor_id in ids_by_type.get("vendor", set()):
                    if vendor_id in vendor_names:
                        labels[("vendor", vendor_id)] = vendor_names[vendor_id]
                for vendor_id in ids_by_type.get("fuel_price", set()):
                    if vendor_id in vendor_names:
                        labels[("fuel_price", vendor_id)] = vendor_names[vendor_id]

            center_ids = ids_by_type.get("service_center", set())
            if center_ids:
                placeholders = ",".join("?" for _ in center_ids)
                cursor = connection.execute(
                    f"SELECT id, name FROM service_centers WHERE id IN ({placeholders})",
                    list(center_ids),
                )
                for row in cursor.fetchall():
                    name = (row[1] or "").strip()
                    labels[("service_center", int(row[0]))] = name or f"service-center-{row[0]}"
    except Exception:
        return labels

    return labels
