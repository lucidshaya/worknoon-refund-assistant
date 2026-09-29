from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import ai, guard, policy
from ..database import get_db
from ..models import Customer, Order, RefundRequest
from ..schemas import RefundRequestIn, RefundRequestOut

router = APIRouter(prefix="/api/refunds", tags=["refunds"])


@router.post("", response_model=RefundRequestOut)
def submit_refund_request(payload: RefundRequestIn, db: Session = Depends(get_db)):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    customer = db.get(Customer, payload.customer_id)
    order = db.get(Order, payload.order_id)
    if order is not None and order.customer_id != payload.customer_id:
        # Order exists but doesn't belong to this customer -- treat as unverifiable.
        order = None

    # 1. Deterministic prompt-injection scan (always runs, independent of AI availability).
    guard_result = guard.scan_message(message)

    # 2. AI-assisted classification (advisory only; falls back to heuristics on failure).
    classification = ai.classify(message, order)

    # 3. Count this customer's requests in the last 90 days (abuse / frequent-requester signal).
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
    recent_count = (
        db.query(RefundRequest)
        .filter(
            and_(
                RefundRequest.customer_id == payload.customer_id,
                RefundRequest.created_at >= ninety_days_ago,
            )
        )
        .count()
    )

    # 4. Deterministic policy decision -- the only source of truth for the outcome.
    result = policy.evaluate(
        policy.PolicyInput(
            order=order,
            claimed_reason=classification.claimed_reason,
            conflicts_with_status=classification.conflicts_with_status,
            ai_suspicious=classification.suspicious,
            injection_flagged=guard_result.flagged,
            recent_request_count=recent_count,
            stated_amount=classification.stated_amount,
        )
    )

    # 5. AI (or template fallback) drafts the customer-facing reply for the *fixed* decision.
    customer_reply = ai.draft_reply(
        decision=result.decision,
        rule_reasoning=result.reasoning,
        order=order,
        customer_name=customer.name if customer else "there",
    )

    audit_trail = {
        "policy_trace": result.trace,
        "classification": {
            "claimed_reason": classification.claimed_reason,
            "conflicts_with_status": classification.conflicts_with_status,
            "suspicious": classification.suspicious,
            "stated_amount": classification.stated_amount,
            "reasoning": classification.reasoning,
            "source": classification.source,
        },
        "guard": {
            "flagged": guard_result.flagged,
            "matched_patterns": guard_result.matched_patterns,
        },
        "recent_request_count": recent_count,
        "ai_available": ai.ai_available(),
    }

    row = RefundRequest(
        customer_id=payload.customer_id,
        order_id=payload.order_id,
        customer_message=message,
        claimed_reason=classification.claimed_reason,
        decision=result.decision,
        decision_source="ai_assisted" if ai.ai_available() else "policy_engine",
        policy_rule_hit=result.rule_hit,
        ai_summary=classification.reasoning,
        customer_reply=customer_reply,
        injection_flag=guard_result.flagged,
        injection_detail=guard_result.detail or None,
        audit_trail=_safe_json(audit_trail),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return RefundRequestOut(
        id=row.id,
        decision=row.decision,
        customer_reply=row.customer_reply,
        policy_rule_hit=row.policy_rule_hit,
        injection_flag=row.injection_flag,
        ai_summary=row.ai_summary,
    )


def _safe_json(obj) -> str:
    import json

    return json.dumps(obj, default=str)
