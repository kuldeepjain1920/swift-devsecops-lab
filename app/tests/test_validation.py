"""Tests for src/api/validation.py — business-rule checks beyond
what Pydantic already enforces at the schema level."""
import pytest
from decimal import Decimal
from src.models.message import PaymentMessage
from src.api.validation import validate_message, ValidationError


def _make_message(**overrides):
    # Helper to build a valid baseline message, then override specific
    # fields per test — keeps each test focused on the one thing it checks.
    defaults = dict(
        sender_id="BANKUS33",
        receiver_id="BANKGB22",
        amount=Decimal("1500.00"),
        currency="USD",
        account_number="1234567890",
    )
    defaults.update(overrides)
    return PaymentMessage(**defaults)


def test_valid_message_passes():
    msg = _make_message()
    # Should not raise — this is the "happy path" baseline every other
    # test's overrides are compared against.
    validate_message(msg)


def test_same_sender_and_receiver_rejected():
    msg = _make_message(receiver_id="BANKUS33")  # same as sender_id
    with pytest.raises(ValidationError, match="sender_id and receiver_id must differ"):
        validate_message(msg)


def test_amount_over_limit_rejected():
    msg = _make_message(amount=Decimal("2000000.00"))  # over the 1,000,000 cap
    with pytest.raises(ValidationError, match="exceeds single-message limit"):
        validate_message(msg)


def test_unsupported_currency_rejected():
    msg = _make_message(currency="JPY")  # not in the {USD, EUR, GBP, INR} allow-list
    with pytest.raises(ValidationError, match="unsupported currency"):
        validate_message(msg)
