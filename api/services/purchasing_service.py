"""Purchasing workflow service."""
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_audit, log_field_update, pick_fields
from src.database import (
    admin_update_requisition,
    fetch_requisition_record,
    get_vendor_fuel_price_for_fuel_type,
    get_vendor_fuel_prices,
    list_requisitions_by_status,
    list_requisitions_filtered,
    list_po_signatories,
    count_requisitions_filtered,
    mark_cc_reconciled,
    mark_po_released,
    record_cc_fill,
    save_requisition_receiving,
    undo_po_release,
    update_approved_settlement_type,
    update_requisition_po,
    upsert_vendor_fuel_prices,
    SETTLEMENT_CREDIT_CARD,
    SETTLEMENT_VENDOR_INVOICE,
)


def list_signatories(db_path: str) -> List[Dict[str, Any]]:
    """Return active users who may sign POs (purchasing.sign_po permission)."""
    rows = list_po_signatories(db_path)
    result: List[Dict[str, Any]] = []
    for row in rows:
        display_name = (row.get("full_name") or row.get("username") or "").strip()
        if not display_name:
            continue
        result.append(
            {
                "id": row["id"],
                "full_name": display_name,
                "username": row.get("username"),
                "role": row.get("role"),
            }
        )
    return result


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
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Update fuel prices for one vendor."""
    before_rows = get_vendor_fuel_prices(db_path)
    before = next((row for row in before_rows if row.get("vendor_id") == vendor_id), {})
    upsert_vendor_fuel_prices(
        db_path,
        vendor_id,
        diesel_price if diesel_price and diesel_price > 0 else None,
        unleaded_price if unleaded_price and unleaded_price > 0 else None,
        premium_price if premium_price and premium_price > 0 else None,
        user_id,
    )
    after_rows = get_vendor_fuel_prices(db_path)
    after = next((row for row in after_rows if row.get("vendor_id") == vendor_id), {})
    log_field_update(
        db_path,
        "fuel_price",
        vendor_id,
        "updated",
        actor,
        before,
        after,
        ["diesel_price", "unleaded_price", "premium_price"],
        metadata={"vendor_name": after.get("vendor_name") or before.get("vendor_name")},
    )


def list_approved(db_path: str) -> List[Dict[str, Any]]:
    """List approved vendor-invoice requisitions awaiting PO generation."""
    rows = list_requisitions_filtered(
        db_path, ["approved"], settlement_type=SETTLEMENT_VENDOR_INVOICE
    )
    for row in rows:
        default_price = get_vendor_fuel_price_for_fuel_type(
            db_path, row.get("vendor_id"), row.get("fuel_type")
        )
        row["default_unit_price"] = default_price
    return rows


def list_cc_fills_approved(db_path: str) -> List[Dict[str, Any]]:
    """List approved credit-card requisitions awaiting fill recording."""
    rows = list_requisitions_filtered(
        db_path, ["approved"], settlement_type=SETTLEMENT_CREDIT_CARD
    )
    for row in rows:
        default_price = get_vendor_fuel_price_for_fuel_type(
            db_path, row.get("vendor_id"), row.get("fuel_type")
        )
        row["default_unit_price"] = default_price
    return rows


def list_po_generated(db_path: str) -> List[Dict[str, Any]]:
    """List PO-generated requisitions awaiting release."""
    return list_requisitions_by_status(db_path, ["po_generated"])


def list_released_awaiting_receipt(db_path: str) -> List[Dict[str, Any]]:
    """List released POs awaiting vendor receipt."""
    return list_requisitions_by_status(db_path, ["released"])


def list_received_awaiting_billing(db_path: str) -> List[Dict[str, Any]]:
    """List received requisitions editable by purchaser until billed."""
    return list_requisitions_by_status(db_path, ["received"])


def get_queue_counts(db_path: str) -> Dict[str, int]:
    """Return item counts for purchasing sidebar badges."""
    return {
        "approved": count_requisitions_filtered(
            db_path, ["approved"], settlement_type=SETTLEMENT_VENDOR_INVOICE
        ),
        "cc_fills": count_requisitions_filtered(
            db_path, ["approved"], settlement_type=SETTLEMENT_CREDIT_CARD
        ),
        "po_generated": count_requisitions_filtered(db_path, ["po_generated"]),
        "released": count_requisitions_filtered(db_path, ["released"]),
        "received": count_requisitions_filtered(db_path, ["received"]),
    }


def save_receiving(
    db_path: str,
    requisition_id: int,
    received_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    user_role: str = "",
    actor: Optional[Dict[str, Any]] = None,
    is_update: bool = False,
    receiving_remarks: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None,
) -> None:
    """Record or update delivery details (released or received; admin may skip release)."""
    before = fetch_requisition_record(db_path, requisition_id)
    save_requisition_receiving(
        db_path,
        requisition_id,
        received_date,
        actual_unit_price,
        actual_quantity,
        receipt_number,
        user_role=user_role,
        receiving_remarks=receiving_remarks,
        user=user,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    action = "receiving_updated" if is_update else "received"
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        action,
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )


def release_po(
    db_path: str,
    requisition_id: int,
    released_by_user_id: int,
    released_date: str,
    remarks: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Mark PO as released to driver."""
    before = fetch_requisition_record(db_path, requisition_id)
    mark_po_released(
        db_path,
        requisition_id,
        released_by_user_id,
        released_date,
        remarks,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "released",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )


def undo_release_po(
    db_path: str,
    requisition_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Revert released PO to po_generated (superuser only)."""
    before = fetch_requisition_record(db_path, requisition_id)
    undo_po_release(db_path, requisition_id)
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "release_undone",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )


def generate_po(
    db_path: str,
    requisition_id: int,
    unit_price: float,
    po_reference: str,
    prepared_by_user_id: Optional[int],
    signatory_user_id: int,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate PO for an approved requisition."""
    if unit_price <= 0:
        raise RuntimeError("Unit price is required to generate PO.")
    if not signatory_user_id:
        raise RuntimeError("PO signatory is required.")
    before = fetch_requisition_record(db_path, requisition_id)
    update_requisition_po(
        db_path,
        requisition_id,
        po_reference.strip(),
        unit_price,
        prepared_by_user_id,
        signatory_user_id,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    metadata: Dict[str, Any] = {"serial_number": after.get("serial_number")}
    workflow_approver = (before.get("approved_by") or "").strip()
    signatory_name = (after.get("po_signatory") or "").strip()
    if (
        workflow_approver
        and signatory_name
        and workflow_approver.lower() != signatory_name.lower()
    ):
        metadata["workflow_approved_by"] = workflow_approver
        metadata["po_signatory"] = signatory_name
        metadata["signatory_mismatch"] = True
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "po_generated",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
        metadata=metadata,
    )


def admin_edit(
    db_path: str,
    requisition_id: int,
    fields: Dict[str, Any],
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Superuser full edit of any requisition fields."""
    if not fields:
        raise RuntimeError("No fields to update.")
    before = fetch_requisition_record(db_path, requisition_id)
    admin_update_requisition(db_path, requisition_id, fields)
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "admin_edit",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
        metadata={"serial_number": after.get("serial_number")},
    )


def update_settlement_type(
    db_path: str,
    requisition_id: int,
    settlement_type: str,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Change payment method on an approved requisition."""
    before = fetch_requisition_record(db_path, requisition_id)
    update_approved_settlement_type(db_path, requisition_id, settlement_type)
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "settlement_updated",
        actor,
        before,
        after,
        ["settlement_type"],
    )


def record_cc_fill_entry(
    db_path: str,
    requisition_id: int,
    fill_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    cc_card_reference: str = "",
    settlement_type: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Record credit card fill (approved → paid_cc)."""
    before = fetch_requisition_record(db_path, requisition_id)
    record_cc_fill(
        db_path,
        requisition_id,
        fill_date,
        actual_unit_price,
        actual_quantity,
        receipt_number,
        cc_card_reference,
        settlement_type,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "cc_fill_recorded",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
    )
