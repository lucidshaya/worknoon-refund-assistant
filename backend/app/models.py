"""SQLAlchemy ORM models for the mock CRM + audit log."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True)  # e.g. "CUST-001"
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    signup_date = Column(DateTime, nullable=False)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)  # e.g. "ORD-1001"
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    item_name = Column(String, nullable=False)
    order_total = Column(Float, nullable=False)
    order_date = Column(DateTime, nullable=False)
    delivery_date = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="delivered")
    # delivered | in_transit | cancelled | returned
    final_sale = Column(Boolean, nullable=False, default=False)

    customer = relationship("Customer", back_populates="orders")


class RefundRequest(Base):
    """Audit log: one row per refund request processed by the system."""

    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    customer_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    customer_message = Column(Text, nullable=False)
    claimed_reason = Column(String, nullable=True)  # damaged | wrong_item | not_delivered | changed_mind | other

    # Outcome
    decision = Column(String, nullable=False)  # approved | denied | escalated
    decision_source = Column(String, nullable=False)  # policy_engine | ai_assisted
    policy_rule_hit = Column(String, nullable=True)
    ai_summary = Column(Text, nullable=True)
    customer_reply = Column(Text, nullable=False)

    # Security
    injection_flag = Column(Boolean, default=False, nullable=False)
    injection_detail = Column(Text, nullable=True)

    # Full audit trail as JSON text (policy trace, AI raw output, etc.)
    audit_trail = Column(Text, nullable=True)

    resolved_by_human = Column(Boolean, default=False, nullable=False)
    human_note = Column(Text, nullable=True)
