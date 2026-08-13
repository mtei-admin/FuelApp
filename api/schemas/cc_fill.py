"""Credit card fill and reconciliation schemas."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SettlementType = Literal["vendor_invoice", "credit_card"]


class RecordCcFillRequest(BaseModel):
    """Payload to record a credit card fill at the pump."""

    fill_date: str = Field(..., min_length=1)
    actual_unit_price: float = Field(..., gt=0)
    actual_quantity: float = Field(..., gt=0)
    receipt_number: str = Field(..., min_length=1)
    cc_card_reference: str = ""
    settlement_type: Optional[SettlementType] = None


class SettlementTypeUpdateRequest(BaseModel):
    """Change payment method on an approved requisition."""

    settlement_type: SettlementType


class ReconcileCcRequest(BaseModel):
    """Batch reconcile credit card fills; statement reference is optional."""

    requisition_ids: List[int] = Field(..., min_length=1)
    statement_reference: str = ""
