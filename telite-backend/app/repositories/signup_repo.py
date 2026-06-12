from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select

from app.models.pending_verification import PendingVerification
from app.repositories.base_repo import BaseRepository

class SignupRepository(BaseRepository[PendingVerification]):
    model = PendingVerification

    def create_pending(self, data: dict) -> PendingVerification:
        # data should contain email, full_name, password_hash, role_name, domain_type, organization_name, organization_id, etc.
        data["id"] = f"pv-{uuid.uuid4().hex[:12]}"
        pv = PendingVerification(**data)
        self.session.add(pv)
        self.session.flush()
        return pv

    def get_by_email(self, email: str) -> PendingVerification | None:
        stmt = select(PendingVerification).where(PendingVerification.email == email.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def list_pending_by_org(self, org_id: int) -> Sequence[PendingVerification]:
        stmt = (
            select(PendingVerification)
            .where(PendingVerification.organization_id == org_id)
            .where(PendingVerification.status == "pending")
            .order_by(PendingVerification.created_at.desc())
        )
        return self.session.execute(stmt).scalars().all()
        
    def count_pending(self, org_id: int) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(PendingVerification)
            .where(PendingVerification.organization_id == org_id)
            .where(PendingVerification.status == "pending")
        )
        return self.session.execute(stmt).scalar_one()

    def update_status(self, verification_id: str, status: str, reviewed_by: str | None = None, reason: str | None = None) -> PendingVerification:
        pv = self.get_by_id(verification_id)
        if not pv:
            raise ValueError("Verification request not found.")
        
        pv.status = status
        pv.reviewed_by = reviewed_by
        pv.reviewed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if reason:
            pv.rejection_reason = reason
        self.session.flush()
        return pv
