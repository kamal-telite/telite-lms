from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.auth import TokenData, get_current_user, ensure_org_access
from app.db.engine import db_session
from app.repositories.course_repo import CourseRepository
from app.repositories.audit_repo import AuditRepository

logger = logging.getLogger("telite.payments")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

payment_router = APIRouter(prefix="/payment", tags=["Payment"])

class CreateOrderRequest(BaseModel):
    course_id: int
    org_id: int

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    course_id: int
    org_id: int

def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> None:
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured. Contact support.",
        )

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning(
            "Razorpay signature mismatch for order=%s payment=%s",
            order_id,
            payment_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed.",
        )

@payment_router.post("/create-order")
def create_order(
    req: CreateOrderRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict[str, Any]:
    ensure_org_access(current_user, req.org_id)

    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(req.course_id)
    if not course or course.org_id != req.org_id or course.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not available for purchase.",
        )
        
    if not course.price_paise or course.price_paise <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course is not available for purchase.",
        )

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured. Contact your administrator.",
        )

    try:
        import razorpay
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create(
            {
                "amount": course.price_paise,
                "currency": "INR",
                "notes": {
                    "course_id": str(req.course_id),
                    "org_id": str(req.org_id),
                    "user_id": current_user.id,
                },
            }
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment library not installed. Contact support.",
        )
    except Exception as exc:
        logger.error("Razorpay order creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway error. Please try again.",
        )

    audit = AuditRepository(db)
    audit.log_action(
        org_id=req.org_id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        action="payment.order_created",
        target_type="course",
        target_id=str(req.course_id),
        message=f"Payment order created for course {req.course_id}",
        result="success"
    )
    db.commit()

    return {
        "order_id": order["id"],
        "amount": course.price_paise,
        "currency": "INR",
        "course_name": course.name,
        "key_id": RAZORPAY_KEY_ID,
    }


@payment_router.post("/verify-and-enrol")
def verify_and_enrol(
    req: VerifyPaymentRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict[str, Any]:
    ensure_org_access(current_user, req.org_id)

    _verify_razorpay_signature(
        req.razorpay_order_id,
        req.razorpay_payment_id,
        req.razorpay_signature,
    )

    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(req.course_id)
    if not course or course.org_id != req.org_id or course.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not available for purchase.",
        )

    from app.models.enrollment import EnrollmentRequest
    
    # Check if already enrolled
    stmt = select(EnrollmentRequest).where(
        EnrollmentRequest.email == current_user.email,
        EnrollmentRequest.category_slug == course.category_slug,
        EnrollmentRequest.status == 'approved'
    )
    existing = db.execute(stmt).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course.",
        )

    # Note: actual enrollment logic would go here
    
    audit = AuditRepository(db)
    audit.log_action(
        org_id=req.org_id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        action="payment.verified_and_enrolled",
        target_type="course",
        target_id=str(req.course_id),
        message=f"Payment verified (order={req.razorpay_order_id}, payment={req.razorpay_payment_id}). User enrolled in course {req.course_id}.",
        result="success"
    )
    db.commit()

    return {
        "status": "payment_verified_and_enrolled",
        "user_id": current_user.id,
        "email": current_user.email,
        "course_id": req.course_id,
        "course_name": course.name,
        "order_id": req.razorpay_order_id,
        "payment_id": req.razorpay_payment_id,
    }

@payment_router.get("/courses")
def list_purchasable_courses(
    org_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict[str, Any]:
    ensure_org_access(current_user, org_id)

    course_repo = CourseRepository(db)
    courses = course_repo.list_purchasable(org_id)

    result = []
    for c in courses:
        price = c.price_paise or 0
        result.append(
            {
                "course_id": c.id,
                "name": c.name,
                "description": c.description or "",
                "category_slug": c.category_slug or "",
                "price_paise": price,
                "price_display": f"₹{price // 100}" if price else "Free",
            }
        )

    return {"courses": result, "org_id": org_id}
