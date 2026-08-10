from decimal import Decimal
from src.models.message import PaymentMessage

class ValidationError(Exception):
    """Raised when a message fails business-rule validation."""
    pass

def validate_message(msg: PaymentMessage) -> None:
    # Pydantic already enforces type/format constraints (see models/message.py).
    # This layer adds business rules Pydantic can't express declaratively.

    if msg.sender_id == msg.receiver_id:
        raise ValidationError("sender_id and receiver_id must differ")

    if msg.amount > Decimal("1000000.00"):
        # Arbitrary large-amount guardrail — mirrors real payment
        # controls that flag high-value transactions for extra review.
        raise ValidationError("amount exceeds single-message limit")

    # Currency allow-list keeps the demo scoped; a real system would
    # check against an ISO 4217 reference table.
    if msg.currency not in {"USD", "EUR", "GBP", "INR"}:
        raise ValidationError(f"unsupported currency: {msg.currency}")
