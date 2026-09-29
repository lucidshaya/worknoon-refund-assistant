from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer, RefundRequest
from ..schemas import AuditLogOut, CustomerOut, ResolveIn, StatsOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/requests", response_model=list[AuditLogOut])
def list_requests(db: Session = Depends(get_db), limit: int = 100):
    rows = (
        db.query(RefundRequest)
        .order_by(RefundRequest.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return rows


@router.get("/requests/{request_id}", response_model=AuditLogOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    row = db.get(RefundRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return row


@router.post("/requests/{request_id}/resolve", response_model=AuditLogOut)
def resolve_request(request_id: int, payload: ResolveIn, db: Session = Depends(get_db)):
    row = db.get(RefundRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if payload.decision not in ("approved", "denied"):
        raise HTTPException(status_code=422, detail="decision must be 'approved' or 'denied'")

    row.decision = payload.decision
    row.resolved_by_human = True
    row.human_note = payload.note
    db.commit()
    db.refresh(row)
    return row


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(RefundRequest.id)).scalar() or 0
    approved = db.query(func.count(RefundRequest.id)).filter(RefundRequest.decision == "approved").scalar() or 0
    denied = db.query(func.count(RefundRequest.id)).filter(RefundRequest.decision == "denied").scalar() or 0
    escalated = db.query(func.count(RefundRequest.id)).filter(RefundRequest.decision == "escalated").scalar() or 0
    injection_attempts = db.query(func.count(RefundRequest.id)).filter(RefundRequest.injection_flag.is_(True)).scalar() or 0
    return StatsOut(total=total, approved=approved, denied=denied, escalated=escalated, injection_attempts=injection_attempts)


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.id).all()
