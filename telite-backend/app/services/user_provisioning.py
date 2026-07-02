"""
UserProvisioningService
Consolidates all learner onboarding and identity creation logic.
"""
from __future__ import annotations

import uuid
import json
from datetime import datetime, timedelta
from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.invitation import OrgInvitation

from app.repositories.user_repo import UserRepository
from app.repositories.invite_repo import InviteRepository

from app.repositories.audit_repo import AuditRepository
from app.core.password_utils import get_default_learner_password, hash_password


class ProvisioningError(Exception):
    pass


RESERVED_USERNAMES = {
    "admin", "administrator", "superadmin", "root", "support", 
    "api", "system", "telite", "owner", "guest", "test"
}


class UserProvisioningService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.invite_repo = InviteRepository(db)

        self.audit_repo = AuditRepository(db)



    def invite_admin(
        self,
        email: str,
        username: str,
        full_name: str,
        role: str,
        org_id: int,
        actor: User,
        category_scope: str | None = None,
    ) -> OrgInvitation:
        """Invite an admin user to an organization."""
        email = email.lower().strip()
        username = username.lower().strip()

        if username in RESERVED_USERNAMES:
            raise ProvisioningError(f"Username '{username}' is reserved and cannot be used")

        if self.user_repo.get_by_identifier(username):
            raise ProvisioningError("Username is already taken globally")
            
        existing_inv_user = self.db.query(OrgInvitation).filter(
            OrgInvitation.username == username,
            OrgInvitation.revoked_at == None,
            OrgInvitation.accepted_at == None
        ).first()
        if existing_inv_user:
            raise ProvisioningError("Username is already taken globally")

        existing_user = self.user_repo.get_by_identifier(email)
        if existing_user:
            if existing_user.org_id != org_id:
                raise ProvisioningError("Email already belongs to another organization")
            raise ProvisioningError("User with this email already exists")

        now_str = datetime.utcnow().isoformat()
        existing_inv = self.db.query(OrgInvitation).filter(
            OrgInvitation.email == email,
            OrgInvitation.revoked_at == None,
            OrgInvitation.accepted_at == None,
            OrgInvitation.expires_at > now_str
        ).first()
        if existing_inv:
            if existing_inv.org_id != org_id:
                raise ProvisioningError("Email already belongs to another organization")
            raise ProvisioningError("Email is already invited to this organization")

        # Create invitation
        inv = OrgInvitation(
            org_id=org_id,
            email=email,
            username=username,
            token=uuid.uuid4().hex,
            role=role,
            invited_by=actor.id,
            category_scope=category_scope,
            delivery_status="pending",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat(),
        )
        self.db.add(inv)
        
        self.audit_repo.write(
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="admin.invited",
            target_type="invitation",
            target_id=inv.id,
            org_id=org_id,
            message=f"Invited {email} as {role}",
        )
        return inv

    # ── Acceptance Flow ──────────────────────────────────────────────────────────

    def invite_learner(
        self,
        email: str,
        username: str,
        full_name: str,
        role: str,
        org_id: int,
        actor: User,
        category_scope: str | None = None,
        course_ids: list[str] | None = None,
        expires_in_days: int = 14
    ) -> OrgInvitation:
        """Admin invites a learner. Stores course_ids for future assignment."""
        username = username.strip().lower()
        email = email.strip().lower()
        
        if not username:
            raise ProvisioningError("Username is required")
        
        # Identity uniqueness checks
        existing_user = self.user_repo.get_by_identifier(email)
        if existing_user:
            if existing_user.org_id == org_id:
                raise ProvisioningError("User already exists in this organization")
            else:
                raise ProvisioningError("Email already belongs to another organization")
                
        existing_username = self.user_repo.get_by_identifier(username)
        if existing_username:
            raise ProvisioningError("Username is already taken globally")
            
        existing_inv_user = self.db.query(OrgInvitation).filter(
            OrgInvitation.username == username,
            OrgInvitation.revoked_at == None,
            OrgInvitation.accepted_at == None
        ).first()
        if existing_inv_user:
            raise ProvisioningError("Username is already taken globally")

        now_str = datetime.utcnow().isoformat()
        existing_inv = self.db.query(OrgInvitation).filter(
            OrgInvitation.email == email,
            OrgInvitation.revoked_at == None,
            OrgInvitation.accepted_at == None,
            OrgInvitation.expires_at > now_str
        ).first()
        if existing_inv:
            if existing_inv.org_id != org_id:
                raise ProvisioningError("Email already belongs to another organization")
            raise ProvisioningError("Email is already invited to this organization")
            
        expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        
        # Generate secure token
        token = uuid.uuid4().hex
        
        invitation = OrgInvitation(
            org_id=org_id,
            email=email,
            username=username,
            role=role,
            category_scope=category_scope,
            token=token,
            invited_by=actor.id,
            expires_at=expires_at,
            delivery_status="pending",
            metadata_json=json.dumps({"course_ids": course_ids}) if course_ids else None,
        )
        
        self.db.add(invitation)
        self.db.flush()
        return invitation

    def accept_invitation(self, token: str, password: str, full_name: str | None = None) -> User:
        """User accepts invitation with a token and provides a new password."""
        inv = self.invite_repo.get_by_token(token)
        if not inv:
            raise ProvisioningError("Invitation not found")
            
        if inv.is_expired():
            raise ProvisioningError("Invitation has expired")

        if inv.accepted_at or inv.delivery_status == "accepted":
            raise ProvisioningError("Invitation is already accepted")

        if inv.revoked_at:
            raise ProvisioningError("Invitation has been revoked")
            
        inv.delivery_status = "accepted"
        inv.accepted_at = datetime.utcnow().isoformat()

        existing_user = self.user_repo.get_by_email(inv.email)
        if existing_user:
            if existing_user.org_id != inv.org_id:
                raise ProvisioningError("Email belongs to another organization")
            if existing_user.role != inv.role:
                raise ProvisioningError("Existing account role does not match invitation")
            existing_user.password_hash = hash_password(password)
            if full_name:
                existing_user.full_name = full_name.strip()
            user = existing_user
        else:
            user = self._provision_identity(
                email=inv.email,
                username=inv.username,
                full_name=full_name or inv.email.split("@")[0],
                role=inv.role,
                org_id=inv.org_id,
                password_hash=hash_password(password),
                category_scope=inv.category_scope,
                invited_via="admin_invitation",
            )
        
        if user.role == "super_admin":
            from app.repositories.org_repo import OrgRepository
            from app.models.organization import Organization

            org = self.db.get(Organization, user.org_id)
            if org and org.status != "active":
                OrgRepository(self.db).activate_org(user.org_id)
                self.audit_repo.write(
                    org_id=user.org_id,
                    actor_user_id=user.id,
                    actor_name=user.full_name,
                    target_type="org",
                    target_id=str(user.org_id),
                    action="organization.activated",
                    message=f"Activated organization '{org.name}' after first Super Admin invitation acceptance",
                )

        self.db.commit()
        return user

    def create_password_setup_invitation(
        self,
        *,
        user: User,
        actor: User,
        org_id: int,
        category_scope: str | None = None,
        expires_in_days: int = 14,
    ) -> OrgInvitation:
        """Invite an already-provisioned learner to set their password."""
        email = user.email.strip().lower()
        expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        token = uuid.uuid4().hex

        invitation = OrgInvitation(
            org_id=org_id,
            email=email,
            username=user.username,
            role="learner",
            category_scope=category_scope or user.category_scope,
            token=token,
            invited_by=actor.id,
            expires_at=expires_at,
            delivery_status="pending",
            metadata_json=json.dumps({"purpose": "password_setup", "user_id": user.id}),
        )
        self.db.add(invitation)
        self.db.flush()
        return invitation

    # ── Internal Core ────────────────────────────────────────────────────────────

    def provision_manual_learner(
        self,
        *,
        email: str,
        full_name: str,
        org_id: int,
        actor: User,
        category_scope: str | None,
        enrollment_type: str = "manual",
    ) -> tuple[User, bool]:
        """Create or reuse a learner for admin-authorized manual enrollment."""
        email = email.strip().lower()
        full_name = full_name.strip()

        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            if existing_user.org_id != org_id:
                raise ProvisioningError("Email already belongs to another organization")
            if existing_user.role != "learner":
                raise ProvisioningError("Existing account is not a learner")
            if not existing_user.is_active:
                existing_user = self.user_repo.set_active(existing_user, is_active=True)
            if category_scope and not existing_user.category_scope:
                existing_user.category_scope = category_scope
            if enrollment_type and not existing_user.enrollment_type:
                existing_user.enrollment_type = enrollment_type
            self.db.flush()
            return existing_user, False

        user = self._provision_identity(
            email=email,
            username=None,
            full_name=full_name or email.split("@")[0],
            role="learner",
            org_id=org_id,
            password_hash=hash_password(get_default_learner_password()),
            category_scope=category_scope,
            invited_via="manual_enrollment",
            enrollment_type=enrollment_type,
        )

        self.audit_repo.write(
            org_id=org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="learner.manual_provisioned",
            target_type="user",
            target_id=user.id,
            message=f"Manually provisioned learner {email}",
        )
        return user, True

    def _provision_identity(
        self,
        email: str,
        username: str | None,
        full_name: str,
        role: str,
        org_id: int,
        password_hash: str,
        category_scope: str | None,
        invited_via: str,
        **extra
    ) -> User:
        """Private method. Single entry point for all identity creation."""
        user = self.user_repo.create_user(
            email=email,
            full_name=full_name,
            role=role,
            org_id=org_id,
            password_hash=password_hash,
            category_scope=category_scope,
            username=username,
            invited_via=invited_via,
            **extra
        )
        
        # Log creation
        self.audit_repo.write(
            org_id=org_id,
            actor_user_id="SYSTEM",
            actor_name="SYSTEM",
            target_type="user",
            target_id=user.id,
            action="provisioned",
            message=f"Provisioned user {email}",
            metadata={"after": user.to_dict()}
        )
        
        return user
        
    def _role_gradients(self, role: str) -> tuple[str, str]:
        if role == "super_admin":
            return ("from-violet-600 to-indigo-600", "text-white")
        if role == "category_admin":
            return ("from-blue-600 to-cyan-600", "text-white")
        if role == "instructor":
            return ("from-emerald-600 to-teal-600", "text-white")
        if role == "reviewer":
            return ("from-amber-500 to-orange-500", "text-white")
        if role == "learner":
            return ("from-slate-100 to-slate-200", "text-slate-800")
        return ("from-slate-100 to-slate-200", "text-slate-800")
