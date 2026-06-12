"""
EnrollmentRepository — enrollment request data access.

Replaces: list_enrollment_requests, fetch_enrollment_request_by_id,
create_manual_enrollment, approve_enrollment_request,
reject_enrollment_request, approve_enrollment_requests_batch, etc.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select

from app.models.enrollment import EnrollmentRequest
from app.repositories.base_repo import BaseRepository


class EnrollmentRepository(BaseRepository[EnrollmentRequest]):
    model = EnrollmentRequest

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_by_org(
        self,
        org_id: int,
        *,
        status: str | None = None,
        category_slug: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[EnrollmentRequest]:
        stmt = select(EnrollmentRequest).where(EnrollmentRequest.org_id == org_id)
        if status:
            stmt = stmt.where(EnrollmentRequest.status == status)
        if category_slug:
            stmt = stmt.where(EnrollmentRequest.category_slug == category_slug)
        stmt = stmt.order_by(EnrollmentRequest.requested_at.desc()).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def count_pending(self, org_id: int | None = None) -> int:
        stmt = select(EnrollmentRequest).where(EnrollmentRequest.status == "pending")
        if org_id is not None:
            stmt = stmt.where(EnrollmentRequest.org_id == org_id)
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return self.session.execute(count_stmt).scalar_one()

    def get_by_email_and_category(
        self, email: str, category_slug: str, org_id: int
    ) -> EnrollmentRequest | None:
        stmt = select(EnrollmentRequest).where(
            EnrollmentRequest.email == email.lower(),
            EnrollmentRequest.category_slug == category_slug,
            EnrollmentRequest.org_id == org_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_request(
        self,
        *,
        full_name: str,
        email: str,
        category_slug: str,
        org_id: int,
        request_type: str = "self",
        **extra: Any,
    ) -> EnrollmentRequest:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        req = EnrollmentRequest(
            id=f"enrol-{uuid.uuid4().hex[:10]}",
            full_name=full_name.strip(),
            email=email.lower().strip(),
            category_slug=category_slug,
            org_id=org_id,
            request_type=request_type,
            status="pending",
            requested_at=now,
            **extra,
        )
        self.session.add(req)
        self.session.flush()
        return req

    def approve(
        self,
        request: EnrollmentRequest,
        *,
        reviewed_by: str,
    ) -> EnrollmentRequest:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        request.status = "approved"
        request.reviewed_by = reviewed_by
        request.reviewed_at = now
        self.session.flush()
        return request

    def reject(
        self,
        request: EnrollmentRequest,
        *,
        reviewed_by: str,
        reason: str | None = None,
    ) -> EnrollmentRequest:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        request.status = "rejected"
        request.reviewed_by = reviewed_by
        request.reviewed_at = now
        request.rejection_reason = reason
        self.session.flush()
        return request

    def batch_approve(
        self,
        request_ids: list[str],
        *,
        reviewed_by: str,
        org_id: int,
    ) -> dict[str, Any]:
        """Approve multiple enrollment requests, scoped to org."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        approved = 0
        failed = []

        for rid in request_ids:
            req = self.get_by_id_and_org(rid, org_id)
            if req is None or req.status != "pending":
                failed.append(rid)
                continue
            req.status = "approved"
            req.reviewed_by = reviewed_by
            req.reviewed_at = now
            approved += 1

        self.session.flush()
        return {
            "approved": approved,
            "failed": failed,
            "total": len(request_ids),
        }

    def has_access(self, user_id: str, course_id: str, org_id: int) -> bool:
        from app.models.user import User
        from app.models.course import Course
        
        course = self.session.execute(
            select(Course).where(Course.id == course_id, Course.org_id == org_id)
        ).scalar_one_or_none()
        
        if not course:
            return False

        user = self.session.execute(
            select(User).where(User.id == user_id, User.org_id == org_id)
        ).scalar_one_or_none()
        
        if not user:
            return False

        if user.role in ("super_admin", "category_admin"):
            return True

        if course.status not in ("active", "published"):
            return False

        if user.category_scope and user.category_scope == course.category_slug:
            return True

        if course.tier == 'free':
            return True

        # Check explicit approved enrollment for this user/email and course category
        stmt = select(EnrollmentRequest).where(
            EnrollmentRequest.email == user.email,
            EnrollmentRequest.category_slug == course.category_slug,
            EnrollmentRequest.org_id == org_id,
            EnrollmentRequest.status == "approved"
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None
