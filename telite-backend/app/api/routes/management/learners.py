"""Learner invitation and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import TokenData, require_admin, resolve_org_scope
from app.db.engine import db_session
from app.repositories.user_repo import UserRepository
from app.repositories.org_repo import OrgRepository
from app.repositories.invite_repo import InviteRepository
from app.services.email import send_invitation_email
from app.services.user_provisioning import UserProvisioningService, ProvisioningError
from app.api.routes.management.schemas import InviteLearnerPayload

learners_router = APIRouter(tags=["Learner Management"])


@learners_router.post("/learners/invite", status_code=201)
def api_invite_learner(
    payload: InviteLearnerPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Invite a learner via email."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    org_repo = OrgRepository(db)
    org = org_repo.get_by_id(scoped_org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    try:
        provision_svc = UserProvisioningService(db)
        invitation = provision_svc.invite_learner(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name,
            role="learner",
            org_id=scoped_org_id,
            actor=actor,
            category_scope=payload.category_scope,
            course_ids=payload.course_ids,
        )
        invitation_id = invitation.id
        invitation_payload = invitation.to_dict()
        db.commit()
    except ProvisioningError as pe:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(pe))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
        
    delivered = send_invitation_email(
        to_email=invitation_payload["email"],
        org_name=org.name,
        org_domain=org.domain,
        role=invitation_payload["role"],
        token=invitation_payload["token"],
        expires_at=str(invitation_payload["expires_at"]),
    )
    
    try:
        invite_repo = InviteRepository(db)
        invite_repo.record_delivery(invitation_id, delivered=delivered)
        db.commit()
        invitation_payload["delivery_status"] = "delivered" if delivered else "failed"
    except:
        db.rollback()
    
    return {"message": "Learner invitation sent successfully", "invitation": invitation_payload}


@learners_router.post("/learners/reinvite/{invitation_id}", status_code=200)
def api_reinvite_learner(
    invitation_id: int,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Reserved for reinviting a learner. Implementation pending."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
