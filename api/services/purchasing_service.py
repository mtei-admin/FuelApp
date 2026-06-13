"""Purchasing workflow service."""
from typing import Any, Dict, List, Optional

from src.database import (
    get_vendor_fuel_price_for_fuel_type,
    get_vendor_fuel_prices,
    list_requisitions_by_status,
    update_requisition_po,
    update_requisition_received,
    upsert_vendor_fuel_prices,
)


def list_fuel_prices(db_path: str) -> List[Dict[str, Any]]:
    """Return all vendors with current fuel prices."""
    return get_vendor_fuel_prices(db_path)


def update_fuel_prices(
    db_path: str,
    vendor_id: int,
    diesel_price: Optional[float],
    unleaded_price: Optional[float],
    premium_price: Optional[float],
    user_id: Optional[int],
) -> None:
    """Update fuel prices for one vendor."""
    upsert_vendor_fuel_prices(
        db_path,
        vendor_id,
        diesel_price if diesel_price and diesel_price > 0 else None,
        unleaded_price if unleaded_price and unleaded_price > 0 else None,
        premium_price if premium_price and premium_price > 0 else None,
        user_id,
    )


def list_approved(db_path: str) -> List[Dict[str, Any]]:
    """List approved requisitions awaiting PO generation."""
    rows = list_requisitions_by_status(db_path, ["approved"])
    for row in rows:
        default_price = get_vendor_fuel_price_for_fuel_type(
            db_path, row.get("vendor_id"), row.get("fuel_type")
        )
        row["default_unit_price"] = default_price
    return rows


def list_po_generated(db_path: str) -> List[Dict[str, Any]]:
    """List PO-generated requisitions awaiting receipt."""
    return list_requisitions_by_status(db_path, ["po_generated"])


def generate_po(
    db_path: str,
    requisition_id: int,
    unit_price: float,
    po_reference: str,
    prepared_by_user_id: Optional[int],
) -> None:
    """Generate PO for an approved requisition."""
    if unit_price <= 0:
        raise RuntimeError("Unit price is required to generate PO.")
    update_requisition_po(
        db_path,
        requisition_id,
        po_reference.strip(),
        unit_price,
        prepared_by_user_id,
    )


def mark_received(db_path: str, requisition_id: int) -> None:
    """Mark a PO-generated requisition as received."""
    update_requisition_received(db_path, requisition_id)
