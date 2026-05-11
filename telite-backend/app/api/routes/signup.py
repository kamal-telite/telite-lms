from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
import pandas as pd
import io
from pydantic import BaseModel, Field

from app.api.auth import TokenData, ensure_org_access, require_admin, require_super_admin, resolve_org_scope
from app.services.email import send_signup_approval_email, send_signup_rejection_email
from app.services.store import (
    approve_pending_verification,
    count_pending_signups,
    create_pending_verification,
    fetch_user_by_id,
    get_pending_verification,
    get_signup_roles,
    list_pending_verifications,
    reject_pending_verification,
    slugify,
    update_user_moodle_id,
)

logger = logging.getLogger("telite.signup")

signup_router = APIRouter(tags=["Signup & Verification"])


def _org_id(record: dict[str, Any] | None) -> int | None:
    if not record:
        return None
    return record.get("org_id") or record.get("organization_id")


# ── Pydantic models ─────────────────────────────────────────────────────────


class SignupPayload(BaseModel):
    domain_type: str = Field(..., description="college or company")
    role_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=5, pattern=r"^\S+@\S+\.\S+$")
    full_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)
    organization_name: str = Field(..., min_length=2)
    phone: str | None = None
    id_number: str | None = None
    program: str | None = None
    branch: str | None = None
    captcha: str = Field(..., min_length=1)


class RejectPayload(BaseModel):
    reason: str | None = None


# ── Public endpoints (no auth required) ──────────────────────────────────────


@signup_router.get("/signup/organizations")
def get_organizations(type: str | None = Query(default=None)):
    from app.services.store import get_conn
    with get_conn() as conn:
        if type:
            rows = conn.execute("SELECT * FROM organizations WHERE type = ?", (type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM organizations").fetchall()
        return [dict(r) for r in rows]


@signup_router.get("/signup/roles/{domain_type}")
def get_roles(domain_type: str):
    """Return the available roles for a given domain type (college or company)."""
    if domain_type not in ("college", "company"):
        raise HTTPException(status_code=400, detail="domain_type must be 'college' or 'company'")
    return {"domain_type": domain_type, "roles": get_signup_roles(domain_type)}


@signup_router.post("/signup/register")
def register(body: SignupPayload):
    """Submit a new signup request. It goes into pending_verifications for admin review."""
    if body.domain_type not in ("college", "company"):
        raise HTTPException(status_code=400, detail="domain_type must be 'college' or 'company'")

    # CAPTCHA validation — the client solves a math challenge; we just verify it's present
    if not body.captcha or not body.captcha.strip():
        raise HTTPException(status_code=400, detail="CAPTCHA is required.")

    valid_roles = [r["value"] for r in get_signup_roles(body.domain_type)]
    if body.role_name not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role_name}' for domain '{body.domain_type}'. Valid roles: {', '.join(valid_roles)}",
        )

    # ── Role-based field enforcement ──────────────────────────────────────
    ROLES_REQUIRING_ID = {"student", "intern", "employee", "project_admin"}
    ROLES_REQUIRING_PROGRAM = {"student", "teacher", "admin"}
    ROLES_REQUIRING_BRANCH = {"student", "teacher", "admin", "intern", "employee", "project_admin"}

    if body.role_name in ROLES_REQUIRING_ID and not (body.id_number or "").strip():
        raise HTTPException(status_code=400, detail="ID Number (Enrollment / Employee / Intern ID) is required for this role.")

    if body.role_name in ROLES_REQUIRING_PROGRAM and not (body.program or "").strip():
        raise HTTPException(status_code=400, detail="Program is required for this role.")

    if body.role_name in ROLES_REQUIRING_BRANCH and not (body.branch or "").strip():
        raise HTTPException(status_code=400, detail="Branch / Department is required for this role.")

    try:
        result = create_pending_verification(body.model_dump())
        logger.info(
            "New signup submitted: email=%s role=%s domain=%s org=%s",
            body.email,
            body.role_name,
            body.domain_type,
            body.organization_name,
        )
        return {
            "status": "pending",
            "message": "Your registration has been submitted and is pending admin approval. You will receive an email once reviewed.",
            "verification_id": result["id"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Admin-only verification endpoints ────────────────────────────────────────


@signup_router.get("/admin/verifications")
def get_verifications(
    status: str | None = Query(default=None),
    domain_type: str | None = Query(default=None),
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    """List all pending verifications (admin-only)."""
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    scoped_org_id = resolve_org_scope(current_user, org_id)

    verifications = list_pending_verifications(status=status, domain_type=domain_type, org_id=scoped_org_id)
    pending_count = count_pending_signups(org_id=scoped_org_id)
    return {
        "verifications": verifications,
        "pending_count": pending_count,
    }


@signup_router.get("/admin/verifications/{verification_id}")
def get_verification_detail(
    verification_id: str,
    current_user: TokenData = Depends(require_admin),
):
    """Get details of a specific verification request."""
    pv = get_pending_verification(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.get("organization_id"))
    return pv


def _process_approval(verification_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    """Helper to approve a signup locally and sync to Moodle."""
    result = approve_pending_verification(verification_id, actor)
    
    # Sync to Moodle
    try:
        from app.integrations.moodle_bridge import moodle_create_user
        m_res = moodle_create_user(
            username=result["username"],
            password="Learner@1234",
            firstname=result["full_name"].split()[0],
            lastname=result["full_name"].split()[-1] if len(result["full_name"].split()) > 1 else "",
            email=result["email"],
            custom_fields={
                "program": result.get("program"),
                "branch": result.get("branch"),
                "id_number": result.get("id_number"),
            }
        )
        if m_res.get("user_id"):
            update_user_moodle_id(result["user_id"], m_res["user_id"])
            result["moodle_id"] = m_res["user_id"]
    except Exception as m_exc:
        logger.error("Failed to sync approved user to Moodle: %s", m_exc)

    # Send approval email
    try:
        from app.services.email import send_signup_approval_email
        send_signup_approval_email(
            to_email=result["email"],
            name=result["full_name"],
            role=result["signup_role"],
            username=result["username"],
        )
    except Exception as email_exc:
        logger.warning("Failed to send approval email: %s", email_exc)
        
    return result


@signup_router.post("/admin/verifications/{verification_id}/approve")
def approve_verification(
    verification_id: str,
    current_user: TokenData = Depends(require_admin),
):
    """Approve a pending signup request. Moves the user to the users table and sends an email."""
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    pv = get_pending_verification(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.get("organization_id"))

    try:
        result = _process_approval(verification_id, actor)
        logger.info(
            "Signup approved: email=%s role=%s by=%s",
            result["email"],
            result["signup_role"],
            actor["full_name"],
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@signup_router.post("/admin/verifications/{verification_id}/reject")
def reject_verification(
    verification_id: str,
    body: RejectPayload,
    current_user: TokenData = Depends(require_admin),
):
    """Reject a pending signup request and optionally send a rejection email."""
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    pv = get_pending_verification(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.get("organization_id"))

    try:
        result = reject_pending_verification(verification_id, actor, body.reason)
        logger.info(
            "Signup rejected: email=%s role=%s reason=%s by=%s",
            result["email"],
            result["role_name"],
            result["reason"],
            actor["full_name"],
        )

        # Send rejection email (best-effort)
        try:
            send_signup_rejection_email(
                to_email=result["email"],
                name=result["full_name"],
                role=result["role_name"],
                reason=result["reason"],
            )
        except Exception as email_exc:
            logger.warning("Failed to send rejection email: %s", email_exc)

        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@signup_router.get("/admin/verifications/stats")
def verification_stats(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    """Quick stats for the admin dashboard."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    all_verifications = list_pending_verifications(org_id=scoped_org_id)
    pending = [v for v in all_verifications if v["status"] == "pending"]
    approved = [v for v in all_verifications if v["status"] == "approved"]
    rejected = [v for v in all_verifications if v["status"] == "rejected"]
    return {
        "total": len(all_verifications),
        "pending": len(pending),
        "approved": len(approved),
        "rejected": len(rejected),
    }


@signup_router.post("/admin/verifications/bulk-upload")
async def bulk_upload_verifications(
    file: UploadFile = File(...),
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    """Upload Excel/CSV file to bulk approve/reject pending verifications."""
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file format: {str(e)}")

    # Expected columns: Name, Email, ID, Role, Program, Branch, Organization
    df.columns = df.columns.str.lower().str.strip()
    
    if "email" not in df.columns:
        raise HTTPException(status_code=400, detail="File must contain an 'email' column.")
        
    # Process each row
    scoped_org_id = resolve_org_scope(current_user, org_id)
    pending_users = list_pending_verifications(status="pending", org_id=scoped_org_id)
    pending_by_email = {u["email"].lower(): u for u in pending_users}
    
    approved_count = 0
    rejected_count = 0
    skipped_count = 0
    errors = []
    
    valid_emails_in_file = set(df["email"].dropna().astype(str).str.lower().tolist())
    
    for email, pv in pending_by_email.items():
        if email in valid_emails_in_file:
            try:
                _process_approval(pv["id"], actor)
                approved_count += 1
            except Exception as e:
                errors.append(f"Failed to approve {pv['email']}: {str(e)}")
        else:
            try:
                reject_pending_verification(pv["id"], actor, "Not found in approved Excel list.")
                rejected_count += 1
                try:
                    send_signup_rejection_email(
                        to_email=pv["email"],
                        name=pv["full_name"],
                        role=pv["role_name"],
                        reason="Not found in approved Excel list."
                    )
                except:
                    pass
            except Exception as e:
                errors.append(f"Failed to reject {pv['email']}: {str(e)}")

    return {
        "status": "success",
        "processed": {
            "approved": approved_count,
            "rejected": rejected_count,
            "skipped": skipped_count
        },
        "errors": errors
    }
