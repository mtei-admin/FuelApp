"""Billing workflow service."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_field_update
from src.database import (
    fetch_requisition_record,
    list_requisitions_filtered,
    count_requisitions_filtered,
    mark_cc_reconciled,
    unbill_requisition,
    update_billed_invoice_number,
    update_requisition_actual_quantity,
    update_requisition_billed,
    SETTLEMENT_VENDOR_INVOICE,
)


def list_received(db_path: str) -> List[Dict[str, Any]]:
    """List received vendor-invoice requisitions awaiting billing (excludes CC)."""
    return list_requisitions_filtered(
        db_path, ["received"], settlement_type=SETTLEMENT_VENDOR_INVOICE
    )


def list_billed(db_path: str) -> List[Dict[str, Any]]:
    """List billed vendor-invoice requisitions (for accounting corrections)."""
    return list_requisitions_filtered(
        db_path, ["billed"], settlement_type=SETTLEMENT_VENDOR_INVOICE
    )


def list_cc_unreconciled(db_path: str) -> List[Dict[str, Any]]:
    """List paid credit-card fills awaiting statement reconciliation."""
    return list_requisitions_filtered(
        db_path, ["paid_cc"], cc_unreconciled_only=True
    )


def get_billing_counts(db_path: str) -> Dict[str, int]:
    """Return counts for billing UI badges."""
    return {
        "received": len(list_received(db_path)),
        "cc_unreconciled": count_requisitions_filtered(
            db_path, ["paid_cc"], cc_unreconciled_only=True
        ),
    }


def reconcile_cc(
    db_path: str,
    requisition_ids: List[int],
    statement_reference: str = "",
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Mark credit card fills reconciled; always assigns a system report number."""
    if not requisition_ids:
        raise RuntimeError("Select at least one item to reconcile.")
    statement_ref = (statement_reference or "").strip()

    unreconciled = list_cc_unreconciled(db_path)
    selected = [row for row in unreconciled if row["id"] in requisition_ids]
    if len(selected) != len(requisition_ids):
        raise RuntimeError(
            "One or more selected items are no longer awaiting reconciliation."
        )

    reconciled_by = (actor or {}).get("full_name") or (actor or {}).get("username") or ""
    before_map = {
        req_id: fetch_requisition_record(db_path, req_id) for req_id in requisition_ids
    }
    report_number = mark_cc_reconciled(
        db_path, requisition_ids, statement_ref, reconciled_by
    )
    for req_id in requisition_ids:
        after = fetch_requisition_record(db_path, req_id)
        log_field_update(
            db_path,
            "requisition",
            req_id,
            "cc_reconciled",
            actor,
            before_map.get(req_id),
            after,
            [
                "cc_statement_reference",
                "cc_reconcile_report_no",
                "cc_reconciled_at",
                "cc_reconciled_by",
            ],
            metadata={
                "statement_reference": statement_ref or None,
                "report_number": report_number,
            },
        )

    return {
        "report_number": report_number,
        "statement_reference": statement_ref,
        "reconciled_date": datetime.now().strftime("%Y-%m-%d"),
        "items": selected,
    }


def set_actual_quantity(
    db_path: str,
    requisition_id: int,
    actual_quantity: float,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update actual quantity for FULLTANK billing."""
    if actual_quantity <= 0:
        raise RuntimeError("Quantity must be greater than 0.")
    before = fetch_requisition_record(db_path, requisition_id)
    update_requisition_actual_quantity(db_path, requisition_id, actual_quantity)
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "actual_quantity_updated",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )


def mark_billed(
    db_path: str,
    requisition_ids: List[int],
    invoice_number: str,
    actor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Mark selected requisitions as billed.

    Returns:
        Summary context for billed PO PDF.
    """
    if not requisition_ids:
        raise RuntimeError("Select at least one item to bill.")

    invoice_num = invoice_number.strip()
    if not invoice_num:
        raise RuntimeError("Vendor billing reference is required.")

    received = list_requisitions_filtered(
        db_path, ["received"], settlement_type=SETTLEMENT_VENDOR_INVOICE
    )
    billed_items = [r for r in received if r["id"] in requisition_ids]
    if len(billed_items) != len(requisition_ids):
        raise RuntimeError("One or more selected items are no longer received.")

    for req_id in requisition_ids:
        before = fetch_requisition_record(db_path, req_id)
        update_requisition_billed(db_path, req_id, invoice_num)
        after = fetch_requisition_record(db_path, req_id)
        log_field_update(
            db_path,
            "requisition",
            req_id,
            "billed",
            actor,
            before,
            after,
            REQUISITION_AUDIT_FIELDS,
            metadata={"invoice_number": invoice_num},
        )

    return {
        "invoice_number": invoice_num,
        "billing_date": datetime.now().strftime("%Y-%m-%d"),
        "items": billed_items,
    }


def update_billing_reference(
    db_path: str,
    requisition_ids: List[int],
    invoice_number: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Change vendor billing reference on one or more billed requisitions.

    Args:
        db_path: Database path.
        requisition_ids: Billed requisition IDs.
        invoice_number: New billing reference.
        actor: Acting user for audit.
    """
    if not requisition_ids:
        raise RuntimeError("Select at least one billed item.")
    invoice_num = invoice_number.strip()
    if not invoice_num:
        raise RuntimeError("Billing reference is required.")

    for req_id in requisition_ids:
        before = fetch_requisition_record(db_path, req_id)
        if not before or (before.get("status") or "").lower() != "billed":
            raise RuntimeError(f"Requisition {req_id} is not billed.")
        update_billed_invoice_number(db_path, req_id, invoice_num)
        after = fetch_requisition_record(db_path, req_id)
        log_field_update(
            db_path,
            "requisition",
            req_id,
            "billing_reference_updated",
            actor,
            before,
            after,
            ["invoice_number", "status", "updated_at"],
            metadata={"invoice_number": invoice_num},
        )


def unbill_items(
    db_path: str,
    requisition_ids: List[int],
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Remove requisitions from a billing batch (back to received, clear invoice).

    Args:
        db_path: Database path.
        requisition_ids: Billed requisition IDs to reverse.
        actor: Acting user for audit.
    """
    if not requisition_ids:
        raise RuntimeError("Select at least one billed item to remove.")

    for req_id in requisition_ids:
        before = fetch_requisition_record(db_path, req_id)
        if not before or (before.get("status") or "").lower() != "billed":
            raise RuntimeError(f"Requisition {req_id} is not billed.")
        unbill_requisition(db_path, req_id)
        after = fetch_requisition_record(db_path, req_id)
        log_field_update(
            db_path,
            "requisition",
            req_id,
            "unbilled",
            actor,
            before,
            after,
            REQUISITION_AUDIT_FIELDS,
            metadata={"previous_invoice_number": before.get("invoice_number")},
        )
