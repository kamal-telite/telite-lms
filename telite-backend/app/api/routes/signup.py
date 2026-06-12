from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
import pandas as pd
import io
from pydantic import BaseModel, Field

from app.api.auth import TokenData, ensure_org_access, require_admin, resolve_org_scope
from app.services.email import send_signup_rejection_email
import sqlalchemy
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.engine import db_session
from app.repositories.user_repo import UserRepository
from app.repositories.org_repo import OrgRepository
from app.repositories.signup_repo import SignupRepository
from app.repositories.audit_repo import AuditRepository
from app.core.password_utils import hash_password


logger = logging.getLogger("telite.signup")

signup_router = APIRouter(tags=["Signup & Verification"])


def _org_id(record: dict[str, Any] | None) -> int | None:
    if not record:
        return None
    return record.get("org_id") or record.get("organization_id")



# ── Static Data ─────────────────────────────────────────────────────────────

SIGNUP_ROLES = {
    "college": [
        {"value": "student", "label": "Student", "description": "Enrolled student at the college"},
        {"value": "teacher", "label": "Teacher", "description": "Faculty member"},
        {"value": "admin", "label": "College Admin", "description": "Administrative staff"},
        {"value": "college_admin", "label": "College Super Admin", "description": "Top-level college administrator"},
    ],
    "company": [
        {"value": "intern", "label": "Intern", "description": "Internship program participant"},
        {"value": "employee", "label": "Employee", "description": "Full-time or part-time employee"},
        {"value": "project_admin", "label": "Project Admin", "description": "Project-level administrator"},
        {"value": "company_admin", "label": "Company Admin", "description": "Top-level company administrator"},
    ],
}

_ROLE_TO_SYSTEM_ROLE = {
    "student": "learner",
    "intern": "learner",
    "teacher": "category_admin",
    "employee": "learner",
    "admin": "category_admin",
    "project_admin": "category_admin",
    "college_admin": "super_admin",
    "company_admin": "super_admin",
}

def get_signup_roles(domain_type: str) -> list[dict[str, str]]:
    return SIGNUP_ROLES.get(domain_type, [])

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
def get_organizations(type: str | None = Query(default=None), db: Session = Depends(db_session)):
    org_repo = OrgRepository(db)
    orgs = org_repo.list_all(org_type=type)
    return [
        {
            "id": org.id,
            "name": org.name,
            "domain": org.domain,
            "type": org.type,
            "status": org.status,
            "branding_colors": org.branding_colors,
        }
        for org in orgs
    ]


@signup_router.get("/signup/roles/{domain_type}")
def get_roles(domain_type: str):
    """Return the available roles for a given domain type (college or company)."""
    if domain_type not in ("college", "company"):
        raise HTTPException(status_code=400, detail="domain_type must be 'college' or 'company'")
    return {"domain_type": domain_type, "roles": get_signup_roles(domain_type)}


@signup_router.post("/signup/register")
def register(body: SignupPayload, db: Session = Depends(db_session)):
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
        org_repo = OrgRepository(db)
        user_repo = UserRepository(db)
        signup_repo = SignupRepository(db)

        org_name = body.organization_name.strip()
        org = org_repo.get_by_name(org_name)
        if not org:
            raise ValueError(f"Organization '{org_name}' not found.")
            
        org_domain = (org.domain or "").strip().lower()
        normalized_domain = org_domain.lstrip("@")
        if not normalized_domain:
            raise ValueError("Organization domain is not configured.")

        email = body.email.strip().lower()
        if not email.endswith(f"@{normalized_domain}"):
            raise ValueError(f"Email domain must match the organization domain (@{normalized_domain}).")

        existing_user = user_repo.get_by_email(email)
        if existing_user:
            raise ValueError("An account with this email already exists.")
            
        existing_pending = signup_repo.get_by_email(email)
        if existing_pending and existing_pending.status == "pending":
            raise ValueError("A registration with this email is already pending review.")

        data = body.model_dump()
        data["password_hash"] = hash_password(data.pop("password"))
        data["organization_id"] = org.id
        data["status"] = "pending"
        pv = signup_repo.create_pending(data)
        db.commit()

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
            "verification_id": pv.id,
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
    db: Session = Depends(db_session),
):
    """List all pending verifications (admin-only)."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    scoped_org_id = resolve_org_scope(current_user, org_id)

    signup_repo = SignupRepository(db)
    from sqlalchemy import select
    from app.models.pending_verification import PendingVerification
    stmt = select(PendingVerification)
    if status: stmt = stmt.where(PendingVerification.status == status)
    if domain_type: stmt = stmt.where(PendingVerification.domain_type == domain_type)
    if scoped_org_id is not None: stmt = stmt.where(PendingVerification.organization_id == scoped_org_id)
    stmt = stmt.order_by(PendingVerification.created_at.desc())
    verifications_orm = db.execute(stmt).scalars().all()
    
    from datetime import datetime
    verifications = [
        {
            "id": v.id,
            "email": v.email,
            "full_name": v.full_name,
            "role_name": v.role_name,
            "domain_type": v.domain_type,
            "organization_name": v.organization_name,
            "organization_id": v.organization_id,
            "phone": v.phone,
            "id_number": v.id_number,
            "program": v.program,
            "branch": v.branch,
            "status": v.status,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v.created_at, datetime) else str(v.created_at),
            "reviewed_by": v.reviewed_by,
            "reviewed_at": v.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v.reviewed_at, datetime) and v.reviewed_at else v.reviewed_at,
            "rejection_reason": v.rejection_reason,
        }
        for v in verifications_orm
    ]
    
    pending_count = signup_repo.count_pending(scoped_org_id) if scoped_org_id else db.scalar(select(sqlalchemy.func.count()).select_from(PendingVerification).where(PendingVerification.status == "pending"))
    return {
        "verifications": verifications,
        "pending_count": pending_count,
    }


@signup_router.get("/admin/verifications/{verification_id}")
def get_verification_detail(
    verification_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Get details of a specific verification request."""
    signup_repo = SignupRepository(db)
    pv = signup_repo.get_by_id(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.organization_id)
    return {
            "id": pv.id,
            "email": pv.email,
            "full_name": pv.full_name,
            "role_name": pv.role_name,
            "domain_type": pv.domain_type,
            "organization_name": pv.organization_name,
            "organization_id": pv.organization_id,
            "phone": pv.phone,
            "id_number": pv.id_number,
            "program": pv.program,
            "branch": pv.branch,
            "status": pv.status,
            "created_at": pv.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(pv.created_at, datetime) else str(pv.created_at),
            "reviewed_by": pv.reviewed_by,
            "reviewed_at": pv.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(pv.reviewed_at, datetime) and pv.reviewed_at else pv.reviewed_at,
            "rejection_reason": pv.rejection_reason,
        }


from datetime import timezone
def _process_approval(db: Session, verification_id: str, actor) -> dict[str, Any]:
    """Helper to approve a signup locally and enqueue Moodle sync."""
    signup_repo = SignupRepository(db)
    pv = signup_repo.get_by_id(verification_id)
    if not pv:
        raise ValueError("Verification request not found.")
    if pv.status != "pending":
        raise ValueError(f"This request has already been {pv.status}.")

    actor_org = actor.org_id
    if not actor.is_platform_admin and actor_org != pv.organization_id:
        raise ValueError("You do not have permission to approve users outside your organization.")

    user_repo = UserRepository(db)
    approved_role = _ROLE_TO_SYSTEM_ROLE.get(pv.role_name, pv.role_name)
    
    user = user_repo.create_user(
        email=pv.email,
        full_name=pv.full_name,
        role=approved_role,
        org_id=pv.organization_id,
        password="TMP_WILL_OVERWRITE", 
        program=pv.program,
        branch=pv.branch,
        id_number=pv.id_number,
    )
    user.password_hash = pv.password_hash
    
    pv.status = "approved"
    pv.reviewed_by = actor.id
    pv.reviewed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    audit_repo = AuditRepository(db)
    audit_repo.log_action(
        actor_id=actor.id,
        actor_name=actor.full_name,
        action="signup.approve",
        target_type="pending_verification",
        target_id=verification_id,
        org_id=pv.organization_id,
        message=f"Approved signup request for {pv.email}",
    )
    
    db.commit()

    result = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.org_id,
        "signup_role": pv.role_name,
        "program": user.program,
        "branch": user.branch,
        "id_number": user.id_number,
    }

    # Note: Moodle sync upon user approval has been retired

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
    db: Session = Depends(db_session),
):
    """Approve a pending signup request. Moves the user to the users table and sends an email."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    signup_repo = SignupRepository(db)
    pv = signup_repo.get_by_id(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.organization_id)

    try:
        result = _process_approval(db, verification_id, actor)
        logger.info(
            "Signup approved: email=%s role=%s by=%s",
            result["email"],
            result["signup_role"],
            actor.full_name,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@signup_router.post("/admin/verifications/{verification_id}/reject")
def reject_verification(
    verification_id: str,
    body: RejectPayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Reject a pending signup request and optionally send a rejection email."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    signup_repo = SignupRepository(db)
    pv = signup_repo.get_by_id(verification_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Verification request not found.")
    ensure_org_access(current_user, pv.organization_id)

    try:
        if pv.status != "pending":
            raise ValueError(f"This request has already been {pv.status}.")
            
        actor_org = actor.org_id
        if not actor.is_platform_admin and actor_org != pv.organization_id:
            raise ValueError("You do not have permission to reject users outside your organization.")

        signup_repo.update_status(verification_id, "rejected", reviewed_by=actor.id, reason=body.reason)
        
        audit_repo = AuditRepository(db)
        audit_repo.log_action(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action="signup.reject",
            target_type="pending_verification",
            target_id=verification_id,
            org_id=pv.organization_id,
            message=f"Rejected signup request for {pv.email}. Reason: {body.reason or 'None provided'}",
        )
        db.commit()

        result = {
            "email": pv.email,
            "role_name": pv.role_name,
            "reason": body.reason,
            "full_name": pv.full_name,
        }

        logger.info(
            "Signup rejected: email=%s role=%s reason=%s by=%s",
            result["email"],
            result["role_name"],
            result["reason"],
            actor.full_name,
        )

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
    db: Session = Depends(db_session),
):
    """Quick stats for the admin dashboard."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    from sqlalchemy import select
    from app.models.pending_verification import PendingVerification
    stmt = select(PendingVerification)
    if scoped_org_id is not None:
        stmt = stmt.where(PendingVerification.organization_id == scoped_org_id)
    all_verifications = db.execute(stmt).scalars().all()
    
    pending = [v for v in all_verifications if v.status == "pending"]
    approved = [v for v in all_verifications if v.status == "approved"]
    rejected = [v for v in all_verifications if v.status == "rejected"]
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
    db: Session = Depends(db_session),
):
    """Upload Excel/CSV file to bulk approve/reject pending verifications."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
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
    
    signup_repo = SignupRepository(db)
    from sqlalchemy import select
    from app.models.pending_verification import PendingVerification
    stmt = select(PendingVerification).where(PendingVerification.status == "pending")
    if scoped_org_id is not None:
        stmt = stmt.where(PendingVerification.organization_id == scoped_org_id)
    pending_users = db.execute(stmt).scalars().all()
    
    pending_by_email = {u.email.lower(): u for u in pending_users}
    
    approved_count = 0
    rejected_count = 0
    skipped_count = 0
    errors = []
    
    valid_emails_in_file = set(df["email"].dropna().astype(str).str.lower().tolist())
    
    for email, pv in pending_by_email.items():
        if email in valid_emails_in_file:
            try:
                _process_approval(db, pv.id, actor)
                approved_count += 1
            except Exception as e:
                errors.append(f"Failed to approve {pv.email}: {str(e)}")
        else:
            try:
                signup_repo.update_status(pv.id, "rejected", reviewed_by=actor.id, reason="Not found in approved Excel list.")
                rejected_count += 1
                try:
                    send_signup_rejection_email(
                        to_email=pv.email,
                        name=pv.full_name,
                        role=pv.role_name,
                        reason="Not found in approved Excel list."
                    )
                except:
                    pass
            except Exception as e:
                errors.append(f"Failed to reject {pv.email}: {str(e)}")

    audit_repo = AuditRepository(db)
    audit_repo.log_action(
        actor_id=actor.id,
        actor_name=actor.full_name,
        action="signup.bulk_review",
        target_type="pending_verification_batch",
        target_id=file.filename or "bulk-upload",
        org_id=scoped_org_id,
        message=f"{actor.full_name} processed signup bulk review file {file.filename or 'bulk-upload'}",
    )
    db.commit()

    return {
        "status": "success",
        "processed": {
            "approved": approved_count,
            "rejected": rejected_count,
            "skipped": skipped_count
        },
        "errors": errors
    }
