"""Receiving (delivery) API schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class ReceiveRequest(BaseModel):
    """Payload to record or update delivery/receipt details."""

    received_date: str = Field(..., min_length=1)
    actual_unit_price: float = Field(..., gt=0)
    actual_quantity: float = Field(..., gt=0)
    receipt_number: str = Field(..., min_length=1)
    remarks: Optional[str] = None
