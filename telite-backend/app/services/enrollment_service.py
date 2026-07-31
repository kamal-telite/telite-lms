"""Native enrollment workflows for TELITE onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.course_version import CourseVersion
from app.models.enrollment import EnrollmentRequest
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.repositories.user_repo import UserRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.invite_repo import InviteRepository
from app.repositories.org_repo import OrgRepository
from app.models.notification import NotificationType
from app.core.notification_payloads import enrollment_notification_metadata
from app.services.email import send_invitation_email
from app.services.user_provisioning import ProvisioningError, UserProvisioningService


class EnrollmentServiceError(Exception):
    """Base error for enrollment workflow failures."""


class EnrollmentPermissionError(EnrollmentServiceError):
    """Raised when the actor cannot enroll into the requested scope."""


@dataclass(frozen=True)
class ManualEnrollmentResult:
    user: User
    enrollment_request: EnrollmentRequest
    enrolled_course_ids: list[str]
    skipped_course_ids: list[str]
    category_slug: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "user": {
                "id": self.user.id,
                "email": self.user.email,
                "full_name": self.user.full_name,
                "role": self.user.role,
                "org_id": self.user.org_id,
                "category_scope": self.user.category_scope,
            },
            "request": self.enrollment_request.to_dict(),
            "category_slug": self.category_slug,
            "enrolled_course_ids": self.enrolled_course_ids,
            "skipped_course_ids": self.skipped_course_ids,
        }


class EnrollmentService:
    """Native enrollment service using Phase O-1 provisioning boundaries."""

    ALLOWED_ACTOR_ROLES = {"platform_admin", "super_admin", "category_admin"}
    LEARNER_VISIBLE_COURSE_STATUSES = {"active", "published"}

    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.enrollment_repo = EnrollmentRepository(db)
        self.progress_repo = ProgressRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.provisioning = UserProvisioningService(db)

    def manual_enroll(
        self,
        *,
        actor_token: TokenData,
        full_name: str,
        email: str,
        course_ids: list[str],
        enrollment_type: str = "manual",
        note: str | None = None,
    ) -> ManualEnrollmentResult:
        if not actor_token.is_platform_admin and actor_token.role not in self.ALLOWED_ACTOR_ROLES:
            raise EnrollmentPermissionError("Admin access required")
        if actor_token.org_id is None:
            raise EnrollmentPermissionError("Organization context is required")

        normalized_course_ids = self._dedupe_course_ids(course_ids)
        if not normalized_course_ids:
            raise EnrollmentServiceError("At least one course is required")

        actor = self.user_repo.get_by_id(actor_token.id)
        if actor is None:
            raise EnrollmentServiceError("Actor not found")

        courses = self._load_and_validate_courses(
            actor_token=actor_token,
            org_id=actor_token.org_id,
            course_ids=normalized_course_ids,
        )
        category_slug = courses[0].category_slug

        try:
            learner, created_new = self.provisioning.provision_manual_learner(
                email=email,
                full_name=full_name,
                org_id=actor_token.org_id,
                actor=actor,
                category_scope=category_slug,
                enrollment_type=enrollment_type,
            )
        except ProvisioningError as exc:
            raise EnrollmentServiceError(str(exc)) from exc
        except IntegrityError as exc:
            self.db.rollback()
            raise EnrollmentServiceError("Email is already assigned to another account") from exc

        if created_new:
            self._send_new_learner_setup_email(
                learner=learner,
                actor=actor,
                org_id=actor_token.org_id,
                category_slug=category_slug,
            )

        enrollment_request = self._ensure_approved_request(
            learner=learner,
            full_name=full_name,
            category_slug=category_slug,
            org_id=actor_token.org_id,
            actor=actor,
            enrollment_type=enrollment_type,
        )

        enrolled_course_ids: list[str] = []
        skipped_course_ids: list[str] = []
        for course in courses:
            existing_progress = self.progress_repo.get_course_progress(
                learner.id,
                course.id,
                actor_token.org_id,
            )
            if existing_progress:
                skipped_course_ids.append(course.id)
                continue

            progress = CourseProgress(
                user_id=learner.id,
                course_id=course.id,
                org_id=actor_token.org_id,
                status="not_started",
                completion_percentage=0.0,
                time_spent_seconds=0,
                enrolled_version=self._latest_published_version_number(course.id, actor_token.org_id),
            )
            self.progress_repo.upsert_course_progress(progress)
            course.enrolled_count = (course.enrolled_count or 0) + 1
            enrolled_course_ids.append(course.id)

            self.notification_repo.create(
                user_id=learner.id,
                org_id=actor_token.org_id,
                title="Course Enrollment",
                body=f"You have been enrolled in '{course.name}'.",
                notif_type=NotificationType.ENROLLMENT_CREATED,
                source_type="course",
                source_id=course.id,
                metadata=enrollment_notification_metadata(course.id),
            )

        self.audit_repo.write(
            org_id=actor_token.org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="enrollment.manual",
            target_type="user",
            target_id=learner.id,
            message=f"Manually enrolled {learner.email} into {len(enrolled_course_ids)} course(s)",
            metadata={
                "category_slug": category_slug,
                "course_ids": normalized_course_ids,
                "enrolled_course_ids": enrolled_course_ids,
                "skipped_course_ids": skipped_course_ids,
                "note": note,
            },
        )

        self.db.flush()

        # ── Note: Enrollment hook dispatch moved to API layer to prevent race condition ──

        return ManualEnrollmentResult(
            user=learner,
            enrollment_request=enrollment_request,
            enrolled_course_ids=enrolled_course_ids,
            skipped_course_ids=skipped_course_ids,
            category_slug=category_slug,
        )

    def _send_new_learner_setup_email(
        self,
        *,
        learner: User,
        actor: User,
        org_id: int,
        category_slug: str,
    ) -> None:
        org = OrgRepository(self.db).get_by_id(org_id)
        if not org:
            return

        invitation = self.provisioning.create_password_setup_invitation(
            user=learner,
            actor=actor,
            org_id=org_id,
            category_scope=category_slug,
        )
        self.db.flush()

        delivered = send_invitation_email(
            to_email=invitation.email,
            org_name=org.name,
            org_domain=org.domain,
            role=invitation.role,
            token=invitation.token,
            expires_at=str(invitation.expires_at),
        )
        InviteRepository(self.db).record_delivery(invitation.id, delivered=delivered)

    def _load_and_validate_courses(
        self,
        *,
        actor_token: TokenData,
        org_id: int,
        course_ids: list[str],
    ) -> list[Course]:
        courses = list(self.course_repo.list_by_ids_for_org(course_ids, org_id))
        found_ids = {course.id for course in courses}
        missing_ids = [course_id for course_id in course_ids if course_id not in found_ids]
        if missing_ids:
            raise EnrollmentPermissionError("One or more courses are unavailable")

        disallowed_status = [
            course.id
            for course in courses
            if (course.status or "").lower() not in self.LEARNER_VISIBLE_COURSE_STATUSES
        ]
        if disallowed_status:
            raise EnrollmentServiceError("Only active or published courses can be enrolled")

        categories = {course.category_slug for course in courses}
        if len(categories) != 1:
            raise EnrollmentServiceError("Manual enrollment supports one category per request")

        category_slug = next(iter(categories))
        if actor_token.role == "category_admin" and not actor_token.is_platform_admin:
            if not actor_token.category_scope or actor_token.category_scope != category_slug:
                raise EnrollmentPermissionError("Category access denied")

        return sorted(courses, key=lambda course: course_ids.index(course.id))

    def _ensure_approved_request(
        self,
        *,
        learner: User,
        full_name: str,
        category_slug: str,
        org_id: int,
        actor: User,
        enrollment_type: str,
    ) -> EnrollmentRequest:
        existing_request = self.enrollment_repo.get_latest_by_email_category_statuses(
            learner.email,
            category_slug,
            org_id,
            statuses=["approved", "pending"],
        )
        if existing_request:
            if existing_request.status == "pending":
                return self.enrollment_repo.approve(existing_request, reviewed_by=actor.id)
            return existing_request

        enrollment_request = self.enrollment_repo.create_request(
            full_name=full_name or learner.full_name,
            email=learner.email,
            category_slug=category_slug,
            org_id=org_id,
            request_type=enrollment_type or "manual",
        )
        return self.enrollment_repo.approve(enrollment_request, reviewed_by=actor.id)

    def _latest_published_version_number(self, course_id: str, org_id: int) -> int | None:
        stmt = (
            select(CourseVersion)
            .where(
                CourseVersion.course_id == course_id,
                CourseVersion.org_id == org_id,
                CourseVersion.status.in_(["published", "Published"]),
            )
            .order_by(CourseVersion.version_number.desc())
            .limit(1)
        )
        version = self.db.execute(stmt).scalar_one_or_none()
        return version.version_number if version else None

    @staticmethod
    def _dedupe_course_ids(course_ids: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for course_id in course_ids:
            value = str(course_id).strip()
            if value and value not in seen:
                normalized.append(value)
                seen.add(value)
        return normalized
