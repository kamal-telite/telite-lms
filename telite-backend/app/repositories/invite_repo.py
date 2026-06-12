from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select

from app.models.invitation import OrgInvitation
from app.repositories.base_repo import BaseRepository

class InviteRepository(BaseRepository[OrgInvitation]):
    model = OrgInvitation

    def get_by_token(self, token: str) -> OrgInvitation | None:
        stmt = select(OrgInvitation).where(OrgInvitation.token == token)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_pending(self, org_id: int | None = None) -> Sequence[OrgInvitation]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        stmt = (
            select(OrgInvitation)
            .where(OrgInvitation.accepted_at.is_(None))
            .where(OrgInvitation.revoked_at.is_(None))
            .where(OrgInvitation.expires_at > now)
            .order_by(OrgInvitation.created_at.desc())
        )
        if org_id is not None:
            stmt = stmt.where(OrgInvitation.org_id == org_id)
            
        return self.session.execute(stmt).scalars().all()

    def create_invitation(
        self,
        *,
        org_id: int,
        email: str,
        role: str,
        invited_by: str | None = None,
    ) -> OrgInvitation:
        # Check for existing pending invitation
        stmt = (
            select(OrgInvitation)
            .where(OrgInvitation.org_id == org_id)
            .where(OrgInvitation.email == email.lower().strip())
            .where(OrgInvitation.accepted_at.is_(None))
            .where(OrgInvitation.revoked_at.is_(None))
            .limit(1)
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing:
            raise ValueError(f"A pending invitation already exists for {email} in this organization.")

        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        
        inv = OrgInvitation(
            org_id=org_id,
            email=email.lower().strip(),
            role=role,
            token=token,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(inv)
        self.session.flush()
        return inv

    def revoke_invitation(self, invitation_id: int, revoked_by: str | None = None, reason: str | None = None) -> OrgInvitation:
        inv = self.get_by_id(invitation_id)
        if not inv:
            raise ValueError("Invitation not found.")
        if inv.accepted_at:
            raise ValueError("Invitation has already been accepted.")
        if inv.revoked_at:
            raise ValueError("Invitation has already been revoked.")
            
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        inv.revoked_at = now
        inv.revoked_by = revoked_by
        inv.revoke_reason = reason
        self.session.flush()
        return inv

    def accept_invitation(self, token: str) -> OrgInvitation:
        inv = self.get_by_token(token)
        if not inv:
            raise ValueError("Invitation not found.")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if inv.expires_at < now:
            raise ValueError("Invitation expired.")
        if inv.accepted_at:
            raise ValueError("Invitation already accepted.")
        if inv.revoked_at:
            raise ValueError("Invitation revoked.")
            
        inv.accepted_at = now
        self.session.flush()
        return inv
