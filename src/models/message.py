from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, UTC
from enum import Enum
import uuid

class MessageStatus(str, Enum):
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    SIGNED = "signed"
    ROUTED = "routed"
    ACKED = "acked"
    NACKED = "nacked"

class PaymentMessage(BaseModel):
    # auto-generated fields — client never sets these directly
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: MessageStatus = MessageStatus.SUBMITTED
    schema_version: str = "1.0"

    # client-provided fields
    sender_id: str = Field(..., max_length=35)
    receiver_id: str = Field(..., max_length=35)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    account_number: str  # will be encrypted before persistence — see §8
