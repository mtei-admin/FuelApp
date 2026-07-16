"""Encoder workflow: company-scoped receipt and CC fill recording."""
from typing import Any, Dict, List, Optional

from src.audit import REQUISITION_AUDIT_FIELDS, log_field_update
from src.database import (
    SETTLEMENT_CREDIT_CARD,
    count_requisitions_filtered,
    fetch_requisition_record,
    fetch_requisition_vehicle_company,
    list_requisitions_filtered,
    record_cc_fill,
    save_requisition_receiving,
)


def encoder_company_from_user(user: Dict[str, Any]) -> str:
    """
    Resolve encoder company scope from the authenticated user.

    Raises:
        RuntimeError: If company is not configured on the account.
    """
    company = (user.get("company") or "").strip()
    if not company:
        raise RuntimeError("Encoder account has no company assigned. Contact an administrator.")
    return company


def _assert_requisition_in_company(
    db_path: str, requisition_id: int, company: str
) -> None:
    """Ensure requisition vehicle belongs to the encoder's company."""
    req_company = fetch_requisition_vehicle_company(db_path, requisition_id)
    if not req_company:
        raise RuntimeError("Requisition not found.")
    if req_company != company:
        raise RuntimeError("This request is outside your company scope.")


def get_queue_counts(db_path: str, company: str) -> Dict[str, int]:
    """Return encoder sidebar badge counts for the user's company."""
    return {
        "released": count_requisitions_filtered(db_path, ["released"], company=company),
        "cc_fills": count_requisitions_filtered(
            db_path,
            ["approved"],
            settlement_type=SETTLEMENT_CREDIT_CARD,
            company=company,
        ),
    }


def list_released(db_path: str, company: str) -> List[Dict[str, Any]]:
    """List released POs awaiting receipt for the encoder's company."""
    return list_requisitions_filtered(db_path, ["released"], company=company)


def list_cc_fills(db_path: str, company: str) -> List[Dict[str, Any]]:
    """List approved credit-card requests awaiting fill for the encoder's company."""
    return list_requisitions_filtered(
        db_path,
        ["approved"],
        settlement_type=SETTLEMENT_CREDIT_CARD,
        company=company,
    )


def record_receipt(
    db_path: str,
    requisition_id: int,
    company: str,
    received_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    receiving_remarks: Optional[str] = None,
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Record vendor receipt for a released PO (encoder; no post-received edits)."""
    _assert_requisition_in_company(db_path, requisition_id, company)
    before = fetch_requisition_record(db_path, requisition_id)
    save_requisition_receiving(
        db_path,
        requisition_id,
        received_date,
        actual_unit_price,
        actual_quantity,
        receipt_number,
        user_role="encoder",
        receiving_remarks=receiving_remarks,
    )
    after = fetch_requisition_record(db_path, requisition_id)
    log_field_update(
        db_path,
        "requisition",
        requisition_id,
        "received",
        actor,
        before,
        after,
        REQUISITION_AUDIT_FIELDS,
        metadata={"encoder_company": company},
    )


def record_cc_fill_entry(
    db_path: str,
    requisition_id: int,
    company: str,
    fill_date: str,
    actual_unit_price: float,
    actual_quantity: float,
    receipt_number: str,
    cc_card_reference: str = "",
    actor: Optional[Dict[str, Any]] = None,
) -> None:
    """Record credit card fill for an approved CC request in the encoder's company."""
    _assert_requisition_in_company(db_path, requisition_id, company)
    before = fetch_requisition_record(db_path, requisition_id)
    record_cc_fill(
        db_path,
        requisition_id,
        fill_date,
        actual_unit_price,
        actual_quantity,
        receipt_number,
        cc_card_reference,
        None,
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
        metadata={"encoder_company": company},
    )
