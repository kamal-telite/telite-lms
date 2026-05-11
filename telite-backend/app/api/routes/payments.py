# telite-backend/payment_routes.py
# Phase 3 — Razorpay payment + auto guest enrolment
#
# Add to requirements.txt:  razorpay==1.4.1
# Get free test keys at: https://dashboard.razorpay.com → Settings → API Keys
# Test UPI ID: success@razorpay  (always succeeds in test mode)

import os
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from app.integrations.moodle_bridge import moodle_create_user, moodle_enrol_student, moodle_get_user_by_username

load_dotenv()

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

payment_router = APIRouter(prefix="/payment", tags=["Payment"])

# ── Course price catalogue (replace with DB in Phase 4) ───────────────────
# course_id → {"name": ..., "price_paise": ...}  (paise = rupees × 100)
COURSE_PRICES = {
    1: {"name": "Data Structures and Algorithms", "price_paise": 49900},   # ₹499
    2: {"name": "Operating Systems",              "price_paise": 49900},
    3: {"name": "Signals and Systems",            "price_paise": 39900},   # ₹399
}


class CreateOrderRequest(BaseModel):
    course_id:  int
    guest_name: str
    email:      str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str
    course_id:           int
    guest_name:          str
    email:               str
    password:            str


# ── Step 1: Create Razorpay order ─────────────────────────────────────────
@payment_router.post("/create-order")
def create_order(req: CreateOrderRequest):
    """
    Guest selects a course → frontend calls this → gets Razorpay order_id
    → frontend opens Razorpay checkout popup → user pays.
    """
    if req.course_id not in COURSE_PRICES:
        raise HTTPException(status_code=404, detail="Course not found or not available for purchase.")

    course = COURSE_PRICES[req.course_id]

    # If Razorpay not configured → return mock order for testing
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return {
            "order_id":    f"order_MOCK_{req.course_id}_{req.email[:6]}",
            "amount":      course["price_paise"],
            "currency":    "INR",
            "course_name": course["name"],
            "key_id":      "rzp_test_MOCK",
            "mock":        True,
            "note":        "Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env for live payments",
        }

    try:
        import razorpay
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order  = client.order.create({
            "amount":   course["price_paise"],
            "currency": "INR",
            "notes": {
                "course_id":  str(req.course_id),
                "guest_name": req.guest_name,
                "email":      req.email,
            },
        })
        return {
            "order_id":    order["id"],
            "amount":      course["price_paise"],
            "currency":    "INR",
            "course_name": course["name"],
            "key_id":      RAZORPAY_KEY_ID,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")


# ── Step 2: Verify payment + auto-enrol ───────────────────────────────────
@payment_router.post("/verify-and-enrol")
def verify_and_enrol(req: VerifyPaymentRequest):
    """
    After payment succeeds, Razorpay calls this with the payment signature.
    We verify the signature → create Moodle user → enrol in course.

    In test mode (no keys configured): skips signature check.
    """
    # Signature verification (skipped in mock mode)
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        expected = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if expected != req.razorpay_signature:
            raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    # Create username from email prefix
    username_base = req.email.split("@")[0].lower().replace(".", "_")
    username      = f"guest_{username_base}"

    # Create Moodle user (or get existing)
    first, *rest = req.guest_name.split(" ", 1)
    moodle_user  = moodle_create_user(
        username=username,
        password=req.password,
        firstname=first,
        lastname=rest[0] if rest else ".",
        email=req.email,
        custom_fields={"user_type": "guest", "course_id": str(req.course_id)},
    )

    if not moodle_user["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Could not create Moodle user: {moodle_user.get('error')}",
        )

    user_id = moodle_user["user_id"]
    enrolled = moodle_enrol_student(user_id, req.course_id)

    course_name = COURSE_PRICES.get(req.course_id, {}).get("name", f"Course {req.course_id}")

    return {
        "status":       "payment_verified_and_enrolled",
        "guest_name":   req.guest_name,
        "email":        req.email,
        "course_id":    req.course_id,
        "course_name":  course_name,
        "moodle": {
            "username":  username,
            "user_id":   user_id,
            "enrolled":  enrolled,
        },
        "next_step": f"Login at http://localhost:8082 with username: {username}",
    }


# ── List available courses for purchase ───────────────────────────────────
@payment_router.get("/courses")
def list_purchasable_courses():
    """Returns all courses available for guest purchase with prices."""
    return {
        "courses": [
            {
                "course_id":   cid,
                "name":        info["name"],
                "price_paise": info["price_paise"],
                "price_inr":   f"₹{info['price_paise'] // 100}",
            }
            for cid, info in COURSE_PRICES.items()
        ]
    }
