"""Tests for src/api/routing.py — confirms the simulated routing flow
completes and returns success for Phase 1's always-succeeds stub."""
from decimal import Decimal
from src.models.message import PaymentMessage
from src.api.routing import route_message


def test_route_message_succeeds():
    msg = PaymentMessage(
        sender_id="BANKUS33",
        receiver_id="BANKGB22",
        amount=Decimal("1500.00"),
        currency="USD",
        account_number="1234567890",
    )
    # Phase 1's routing is a stub that always succeeds (real failure
    # injection is a stretch goal per the runbook) — this test locks
    # in that expected behavior so future changes don't break it silently.
    result = route_message(msg)
    assert result is True
