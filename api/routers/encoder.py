"""Encoder routes: company-scoped receipt and CC fill recording."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import EncodeCcFillUser, EncodeReceiptUser, EncoderUser
from api.core.dependencies import get_db_path
from api.schemas.auth import MessageResponse
from api.schemas.cc_fill import RecordCcFillRequest
from api.schemas.receiving import ReceiveRequest
from api.services import encoder_service

router = APIRouter(prefix="/encoder", tags=["encoder"])


def _err(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/counts")
def encoder_counts_route(
    db_path: Annotated[str, Depends(get_db_path)],
    user: EncoderUser,
) -> dict:
    """Badge counts for encoder encode queues."""
    try:
        company = encoder_service.encoder_company_from_user(user)
        return encoder_service.get_queue_counts(db_path, company)
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/released")
def list_released_route(
    db_path: Annotated[str, Depends(get_db_path)],
    user: EncodeReceiptUser,
) -> List[dict]:
    """Released POs awaiting receipt (company-filtered)."""
    try:
        company = encoder_service.encoder_company_from_user(user)
        return encoder_service.list_released(db_path, company)
    except RuntimeError as error:
        raise _err(error) from error


@router.get("/cc-fills")
def list_cc_fills_route(
    db_path: Annotated[str, Depends(get_db_path)],
    user: EncodeCcFillUser,
) -> List[dict]:
    """Approved credit card requests awaiting fill (company-filtered)."""
    try:
        company = encoder_service.encoder_company_from_user(user)
        return encoder_service.list_cc_fills(db_path, company)
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/received", response_model=MessageResponse)
def record_receipt_route(
    requisition_id: int,
    payload: ReceiveRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: EncodeReceiptUser,
) -> MessageResponse:
    """Record delivery receipt for a released PO (encoder; released only)."""
    try:
        company = encoder_service.encoder_company_from_user(user)
        encoder_service.record_receipt(
            db_path,
            requisition_id,
            company,
            payload.received_date,
            payload.actual_unit_price,
            payload.actual_quantity,
            payload.receipt_number,
            receiving_remarks=payload.remarks,
            actor=user,
        )
        return MessageResponse(message="Receipt recorded")
    except RuntimeError as error:
        raise _err(error) from error


@router.post("/{requisition_id}/record-cc-fill", response_model=MessageResponse)
def record_cc_fill_route(
    requisition_id: int,
    payload: RecordCcFillRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: EncodeCcFillUser,
) -> MessageResponse:
    """Record credit card fill (approved → paid_cc)."""
    try:
        company = encoder_service.encoder_company_from_user(user)
        encoder_service.record_cc_fill_entry(
            db_path,
            requisition_id,
            company,
            payload.fill_date,
            payload.actual_unit_price,
            payload.actual_quantity,
            payload.receipt_number,
            payload.cc_card_reference or "",
            actor=user,
        )
        return MessageResponse(message="Credit card fill recorded")
    except RuntimeError as error:
        raise _err(error) from error
