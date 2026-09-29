"""Synthetic CRM data: ~15 customers with order histories.

Dates are generated relative to "now" (at seed time) using day offsets, so
the eligibility windows in policy.py behave correctly no matter when a
reviewer runs `docker-compose up`. Offsets are chosen deliberately to
exercise every branch of the policy engine (final sale, >$500, damaged
within window, stale order, frequent-requester, etc.) — see the inline
comments and `README.md` -> "Demo scenarios" for a walkthrough.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Customer, Order


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


CUSTOMERS = [
    {"id": "CUST-001", "name": "Ada Okafor", "email": "ada.okafor@example.com", "signup_days_ago": 400},
    {"id": "CUST-002", "name": "Ben Talley", "email": "ben.talley@example.com", "signup_days_ago": 620},
    {"id": "CUST-003", "name": "Chidi Umeh", "email": "chidi.umeh@example.com", "signup_days_ago": 210},
    {"id": "CUST-004", "name": "Dara Fields", "email": "dara.fields@example.com", "signup_days_ago": 55},
    {"id": "CUST-005", "name": "Efe Iyamu", "email": "efe.iyamu@example.com", "signup_days_ago": 900},
    {"id": "CUST-006", "name": "Fiona Marsh", "email": "fiona.marsh@example.com", "signup_days_ago": 130},
    {"id": "CUST-007", "name": "George Bello", "email": "george.bello@example.com", "signup_days_ago": 300},
    {"id": "CUST-008", "name": "Hana Suzuki", "email": "hana.suzuki@example.com", "signup_days_ago": 500},
    {"id": "CUST-009", "name": "Ike Chukwu", "email": "ike.chukwu@example.com", "signup_days_ago": 80},
    {"id": "CUST-010", "name": "Jade Ortiz", "email": "jade.ortiz@example.com", "signup_days_ago": 730},
    {"id": "CUST-011", "name": "Kelechi Nwosu", "email": "kelechi.nwosu@example.com", "signup_days_ago": 45},
    {"id": "CUST-012", "name": "Lena Kowalski", "email": "lena.kowalski@example.com", "signup_days_ago": 365},
    {"id": "CUST-013", "name": "Musa Aliyu", "email": "musa.aliyu@example.com", "signup_days_ago": 150},
    {"id": "CUST-014", "name": "Nia Roberts", "email": "nia.roberts@example.com", "signup_days_ago": 20},
    {"id": "CUST-015", "name": "Omar Haddad", "email": "omar.haddad@example.com", "signup_days_ago": 1000},
]

# Each order: (id, customer_id, item, total, order_days_ago, delivery_days_ago, status, final_sale)
ORDERS = [
    # CUST-001: straightforward, within-window, no-damage-claim refund -> should APPROVE
    ("ORD-1001", "CUST-001", "Wireless Mouse", 29.99, 12, 10, "delivered", False),
    # CUST-002: final sale item -> should DENY regardless of reason
    ("ORD-1002", "CUST-002", "Clearance Bluetooth Speaker (Final Sale)", 45.00, 8, 6, "delivered", True),
    # CUST-003: damaged item, within extended 45-day window -> should APPROVE
    ("ORD-1003", "CUST-003", "Ceramic Blender", 89.50, 40, 38, "delivered", False),
    # CUST-004: high value order (>$500) -> should ESCALATE
    ("ORD-1004", "CUST-004", "4K OLED Monitor", 649.00, 5, 3, "delivered", False),
    # CUST-005: order far outside any window -> should DENY
    ("ORD-1005", "CUST-005", "Desk Lamp", 24.00, 120, 118, "delivered", False),
    # CUST-006: claims "never delivered" but status says delivered -> conflicting -> ESCALATE
    ("ORD-1006", "CUST-006", "Bluetooth Headphones", 79.99, 10, 9, "delivered", False),
    # CUST-007: wrong item shipped, within window -> APPROVE
    ("ORD-1007", "CUST-007", "Running Shoes (Size 10)", 110.00, 15, 13, "delivered", False),
    # CUST-008: final sale AND high value -> DENY (final sale wins, more specific/absolute rule)
    ("ORD-1008", "CUST-008", "Designer Handbag (Final Sale)", 550.00, 4, 2, "delivered", True),
    # CUST-009: frequent requester scenario - three recent orders, all with refund requests
    ("ORD-1009", "CUST-009", "Phone Case", 15.00, 20, 18, "delivered", False),
    ("ORD-1010", "CUST-009", "Screen Protector", 9.00, 15, 13, "delivered", False),
    ("ORD-1011", "CUST-009", "USB-C Cable", 12.00, 5, 3, "delivered", False),
    # CUST-010: order still in transit, refund requested early -> ESCALATE (can't verify delivery)
    ("ORD-1012", "CUST-010", "Air Fryer", 129.99, 3, None, "in_transit", False),
    # CUST-011: within window, no damage claim -> APPROVE
    ("ORD-1013", "CUST-011", "Yoga Mat", 34.99, 7, 5, "delivered", False),
    # CUST-012: outside 30-day window, no damage claim -> DENY
    ("ORD-1014", "CUST-012", "Coffee Grinder", 59.00, 50, 48, "delivered", False),
    # CUST-013: damaged item but OUTSIDE even the 45-day extended window -> DENY
    ("ORD-1015", "CUST-013", "Electric Kettle", 39.99, 60, 58, "delivered", False),
    # CUST-014: brand-new customer, within window, straightforward -> APPROVE
    ("ORD-1016", "CUST-014", "Notebook Set", 18.50, 6, 4, "delivered", False),
    # CUST-015: amount mismatch scenario used at the API layer (customer claims wrong amount) -> ESCALATE
    ("ORD-1017", "CUST-015", "Mechanical Keyboard", 145.00, 9, 7, "delivered", False),
]


def seed(db: Session, reset: bool = False) -> None:
    if reset:
        db.query(Order).delete()
        db.query(Customer).delete()
        db.commit()

    if db.query(Customer).count() > 0:
        return  # already seeded

    for c in CUSTOMERS:
        db.add(
            Customer(
                id=c["id"],
                name=c["name"],
                email=c["email"],
                signup_date=_days_ago(c["signup_days_ago"]),
            )
        )
    db.commit()

    for oid, cust_id, item, total, order_days_ago, delivery_days_ago, status, final_sale in ORDERS:
        db.add(
            Order(
                id=oid,
                customer_id=cust_id,
                item_name=item,
                order_total=total,
                order_date=_days_ago(order_days_ago),
                delivery_date=_days_ago(delivery_days_ago) if delivery_days_ago is not None else None,
                status=status,
                final_sale=final_sale,
            )
        )
    db.commit()


def init_db(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db, reset=reset)
    finally:
        db.close()


if __name__ == "__main__":
    init_db(reset=True)
    print("Seeded database.")
