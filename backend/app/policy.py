"""Deterministic refund-policy engine.

This module is the single authority on Approve / Deny / Escalate. It
implements the decision precedence documented in `policy.md`. Nothing the
AI layer says can change the outcome computed here -- the AI is consulted
only for *inputs* to this engine (claimed reason, conflict/suspicion
flags) and for drafting the customer-facing explanation *after* the
decision is already fixed. This separation is the core security control
against prompt injection and policy-bypass attempts: even a fully
jailbroken LLM response cannot change what this function returns, because
the LLM is never allowed to call it or feed it anything other than a
handful of narrow, validated fields.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .models import Order

STANDARD_WINDOW_DAYS = 30
EXTENDED_WINDOW_DAYS = 45
HIGH_VALUE_THRESHOLD = 500.0
FREQUENT_REQUESTER_THRESHOLD = 3

DAMAGE_REASONS = {"damaged", "wrong_item"}


@dataclass
class PolicyInput:
    order: Optional[Order]
    claimed_reason: str  # damaged | wrong_item | not_delivered | changed_mind | other
    conflicts_with_status: bool
    ai_suspicious: bool
    injection_flagged: bool
    recent_request_count: int  # count of this customer's requests in last 90 days (excluding this one)
    stated_amount: Optional[float] = None  # amount the customer claims, if parseable


@dataclass
class PolicyResult:
    decision: str  # approved | denied | escalated
    rule_hit: str
    reasoning: str
    trace: list[str] = field(default_factory=list)


def _days_since(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def evaluate(pi: PolicyInput) -> PolicyResult:
    trace: list[str] = []

    # Rule 1: order must be verifiable
    if pi.order is None:
        trace.append("Order/customer could not be verified against CRM records.")
        return PolicyResult("escalated", "unverifiable_order", trace[-1], trace)

    order = pi.order
    trace.append(f"Order {order.id}: total=${order.order_total:.2f}, final_sale={order.final_sale}, status={order.status}")

    # Rule 2: prompt injection / manipulation detected
    if pi.injection_flagged:
        trace.append("Prompt-injection / policy-bypass attempt detected in customer message.")
        return PolicyResult("escalated", "prompt_injection_detected", trace[-1], trace)

    # Rule 3: order not yet verifiably delivered (e.g. in_transit) -> can't assess
    if order.status not in ("delivered", "returned") and pi.claimed_reason != "not_delivered":
        trace.append(f"Order status is '{order.status}', not yet delivered; cannot assess refund eligibility.")
        return PolicyResult("escalated", "order_not_delivered_yet", trace[-1], trace)

    # Rule 4: stated amount mismatch
    if pi.stated_amount is not None and abs(pi.stated_amount - order.order_total) > 0.01:
        trace.append(
            f"Customer-stated amount (${pi.stated_amount:.2f}) does not match order total (${order.order_total:.2f})."
        )
        return PolicyResult("escalated", "amount_mismatch", trace[-1], trace)

    # Rule 5: final sale items are never refundable
    if order.final_sale:
        trace.append("Item is marked final sale; not eligible for refund under any circumstance.")
        return PolicyResult("denied", "final_sale_item", trace[-1], trace)

    # Rule 6: claim conflicts with order data on file (e.g. "never delivered" but status=delivered)
    if pi.conflicts_with_status:
        trace.append("Customer's stated reason conflicts with order/delivery data on file.")
        return PolicyResult("escalated", "conflicting_claim", trace[-1], trace)

    # Rule 7: AI flagged the request itself as suspicious independent of the guard heuristics
    if pi.ai_suspicious:
        trace.append("Request flagged as suspicious by AI review layer.")
        return PolicyResult("escalated", "ai_flagged_suspicious", trace[-1], trace)

    # Rule 8: high-value orders always require human review
    if order.order_total > HIGH_VALUE_THRESHOLD:
        trace.append(f"Order total ${order.order_total:.2f} exceeds ${HIGH_VALUE_THRESHOLD:.2f} threshold; requires human review.")
        return PolicyResult("escalated", "high_value_review", trace[-1], trace)

    delivery_date = order.delivery_date or order.order_date
    days_since_delivery = _days_since(delivery_date)
    trace.append(f"{days_since_delivery:.1f} days since delivery.")

    # Rule 9: damaged / wrong item, within extended window -> approve
    if pi.claimed_reason in DAMAGE_REASONS:
        if days_since_delivery <= EXTENDED_WINDOW_DAYS:
            trace.append(f"Damage/wrong-item claim within {EXTENDED_WINDOW_DAYS}-day extended window.")
            return PolicyResult("approved", "damaged_or_wrong_item_within_window", trace[-1], trace)
        trace.append(f"Damage/wrong-item claim but outside {EXTENDED_WINDOW_DAYS}-day extended window.")
        return PolicyResult("denied", "damage_claim_outside_extended_window", trace[-1], trace)

    # Rule 10: frequent requester -> escalate even if otherwise eligible
    if pi.recent_request_count >= FREQUENT_REQUESTER_THRESHOLD:
        trace.append(
            f"Customer has {pi.recent_request_count} refund requests in the last 90 days; possible abuse pattern."
        )
        return PolicyResult("escalated", "frequent_requester", trace[-1], trace)

    # Rule 11: standard window
    if days_since_delivery <= STANDARD_WINDOW_DAYS:
        trace.append(f"Within standard {STANDARD_WINDOW_DAYS}-day refund window.")
        return PolicyResult("approved", "within_standard_window", trace[-1], trace)

    trace.append(f"Outside standard {STANDARD_WINDOW_DAYS}-day refund window; no damage/wrong-item claim.")
    return PolicyResult("denied", "outside_standard_window", trace[-1], trace)
