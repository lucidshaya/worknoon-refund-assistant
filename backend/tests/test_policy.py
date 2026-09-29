from datetime import datetime, timedelta, timezone

import pytest

from app.models import Order
from app.policy import PolicyInput, evaluate


def make_order(**overrides):
    defaults = dict(
        id="ORD-TEST",
        customer_id="CUST-TEST",
        item_name="Widget",
        order_total=50.0,
        order_date=datetime.now(timezone.utc) - timedelta(days=10),
        delivery_date=datetime.now(timezone.utc) - timedelta(days=8),
        status="delivered",
        final_sale=False,
    )
    defaults.update(overrides)
    return Order(**defaults)


def base_input(**overrides):
    defaults = dict(
        order=make_order(),
        claimed_reason="other",
        conflicts_with_status=False,
        ai_suspicious=False,
        injection_flagged=False,
        recent_request_count=0,
        stated_amount=None,
    )
    defaults.update(overrides)
    return PolicyInput(**defaults)


def test_unverifiable_order_escalates():
    result = evaluate(base_input(order=None))
    assert result.decision == "escalated"
    assert result.rule_hit == "unverifiable_order"


def test_injection_always_escalates_even_if_otherwise_approvable():
    result = evaluate(base_input(injection_flagged=True))
    assert result.decision == "escalated"
    assert result.rule_hit == "prompt_injection_detected"


def test_final_sale_denied_even_if_damaged():
    order = make_order(final_sale=True)
    result = evaluate(base_input(order=order, claimed_reason="damaged"))
    assert result.decision == "denied"
    assert result.rule_hit == "final_sale_item"


def test_high_value_escalates_even_within_window():
    order = make_order(order_total=750.0)
    result = evaluate(base_input(order=order))
    assert result.decision == "escalated"
    assert result.rule_hit == "high_value_review"


def test_damaged_within_extended_window_approved():
    order = make_order(
        delivery_date=datetime.now(timezone.utc) - timedelta(days=40),
        order_date=datetime.now(timezone.utc) - timedelta(days=42),
    )
    result = evaluate(base_input(order=order, claimed_reason="damaged"))
    assert result.decision == "approved"
    assert result.rule_hit == "damaged_or_wrong_item_within_window"


def test_damaged_outside_extended_window_denied():
    order = make_order(
        delivery_date=datetime.now(timezone.utc) - timedelta(days=60),
        order_date=datetime.now(timezone.utc) - timedelta(days=62),
    )
    result = evaluate(base_input(order=order, claimed_reason="damaged"))
    assert result.decision == "denied"
    assert result.rule_hit == "damage_claim_outside_extended_window"


def test_standard_window_approved():
    result = evaluate(base_input())
    assert result.decision == "approved"
    assert result.rule_hit == "within_standard_window"


def test_outside_standard_window_denied():
    order = make_order(
        delivery_date=datetime.now(timezone.utc) - timedelta(days=45),
        order_date=datetime.now(timezone.utc) - timedelta(days=47),
    )
    result = evaluate(base_input(order=order))
    assert result.decision == "denied"
    assert result.rule_hit == "outside_standard_window"


def test_conflicting_claim_escalates():
    result = evaluate(base_input(conflicts_with_status=True))
    assert result.decision == "escalated"
    assert result.rule_hit == "conflicting_claim"


def test_frequent_requester_escalates_when_otherwise_approvable():
    result = evaluate(base_input(recent_request_count=3))
    assert result.decision == "escalated"
    assert result.rule_hit == "frequent_requester"


def test_amount_mismatch_escalates():
    result = evaluate(base_input(stated_amount=9999.0))
    assert result.decision == "escalated"
    assert result.rule_hit == "amount_mismatch"


def test_order_not_delivered_yet_escalates():
    order = make_order(status="in_transit", delivery_date=None)
    result = evaluate(base_input(order=order, claimed_reason="other"))
    assert result.decision == "escalated"
    assert result.rule_hit == "order_not_delivered_yet"


def test_ai_suspicious_flag_escalates():
    result = evaluate(base_input(ai_suspicious=True))
    assert result.decision == "escalated"
    assert result.rule_hit == "ai_flagged_suspicious"
