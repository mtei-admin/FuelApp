"""Billing workflow service."""
from datetime import datetime
from typing import Any, Dict, List

from src.database import (
    list_requisitions_by_status,
    update_requisition_actual_quantity,
    update_requisition_billed,
)


def list_received(db_path: str) -> List[Dict[str, Any]]:
    """List received requisitions awaiting billing."""
    return list_requisitions_by_status(db_path, ["received"])


def set_actual_quantity(
    db_path: str,
    requisition_id: int,
    actual_quantity: float,
) -> None:
    """Update actual quantity for FULLTANK billing."""
    if actual_quantity <= 0:
        raise RuntimeError("Quantity must be greater than 0.")
    update_requisition_actual_quantity(db_path, requisition_id, actual_quantity)


def mark_billed(
    db_path: str,
    requisition_ids: List[int],
    invoice_number: str,
) -> Dict[str, Any]:
    """
    Mark selected requisitions as billed.

    Returns:
        Summary context for billed PO PDF.
    """
    if not requisition_ids:
        raise RuntimeError("Select at least one item to bill.")

    received = list_requisitions_by_status(db_path, ["received"])
    billed_items = [r for r in received if r["id"] in requisition_ids]
    if len(billed_items) != len(requisition_ids):
        raise RuntimeError("One or more selected items are no longer received.")

    invoice_num = invoice_number.strip()
    for req_id in requisition_ids:
        update_requisition_billed(db_path, req_id, invoice_num)

    return {
        "invoice_number": invoice_num,
        "billing_date": datetime.now().strftime("%Y-%m-%d"),
        "items": billed_items,
    }
