"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RefundRequestIn(BaseModel):
    customer_id: str = Field(..., examples=["CUST-001"])
    order_id: str = Field(..., examples=["ORD-1001"])
    message: str = Field(
        ...,
        description="The customer's free-text refund request / chat message.",
        examples=["The blender arrived cracked, I'd like a refund please."],
    )


class RefundRequestOut(BaseModel):
    id: int
    decision: str
    customer_reply: str
    policy_rule_hit: Optional[str] = None
    injection_flag: bool
    ai_summary: Optional[str] = None


class OrderOut(BaseModel):
    id: str
    item_name: str
    order_total: float
    order_date: datetime
    delivery_date: Optional[datetime]
    status: str
    final_sale: bool

    class Config:
        from_attributes = True


class CustomerOut(BaseModel):
    id: str
    name: str
    email: str
    orders: list[OrderOut] = []

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    customer_id: Optional[str]
    order_id: Optional[str]
    customer_message: str
    claimed_reason: Optional[str]
    decision: str
    decision_source: str
    policy_rule_hit: Optional[str]
    ai_summary: Optional[str]
    customer_reply: str
    injection_flag: bool
    injection_detail: Optional[str]
    audit_trail: Optional[str]
    resolved_by_human: bool
    human_note: Optional[str]

    class Config:
        from_attributes = True


class ResolveIn(BaseModel):
    decision: str = Field(..., description="approved | denied")
    note: str = Field(default="")


class StatsOut(BaseModel):
    total: int
    approved: int
    denied: int
    escalated: int
    injection_attempts: int
