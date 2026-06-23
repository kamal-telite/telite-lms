"""Announcement runtime repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.announcement import Announcement, AnnouncementAudience, AnnouncementReadState


AUDIENCE_TYPES = {"all", "role", "category", "user"}
ANNOUNCEMENT_STATUSES = {"draft", "published", "archived"}


class AnnouncementRepository:
    def __init__(self, session: Session):
        self.session = session

    def _validate_audience(self, audience_type: str, audience_value: str | None) -> tuple[str, str | None]:
        next_type = audience_type.strip().lower()
        next_value = audience_value.strip() if isinstance(audience_value, str) and audience_value.strip() else None
        if next_type not in AUDIENCE_TYPES:
            raise ValueError("audience_type must be one of: all, role, category, user")
        if next_type == "all":
            return next_type, None
        if not next_value:
            raise ValueError("audience_value is required for role, category, and user audiences")
        return next_type, next_value

    def _validate_status(self, status: str) -> str:
        next_status = status.strip().lower()
        if next_status not in ANNOUNCEMENT_STATUSES:
            raise ValueError("status must be one of: draft, published, archived")
        return next_status

    def create(
        self,
        *,
        org_id: int,
        title: str,
        body: str,
        created_by: str,
        audience_type: str = "all",
        audience_value: str | None = None,
        status: str = "published",
    ) -> Announcement:
        next_status = self._validate_status(status)
        next_audience_type, next_audience_value = self._validate_audience(audience_type, audience_value)
        if not title.strip():
            raise ValueError("title is required")
        if not body.strip():
            raise ValueError("body is required")

        announcement = Announcement(
            org_id=org_id,
            title=title.strip(),
            body=body.strip(),
            status=next_status,
            created_by=created_by,
            published_at=datetime.now(timezone.utc) if next_status == "published" else None,
            archived_at=datetime.now(timezone.utc) if next_status == "archived" else None,
        )
        self.session.add(announcement)
        self.session.flush()
        self.session.add(
            AnnouncementAudience(
                announcement_id=announcement.id,
                org_id=org_id,
                audience_type=next_audience_type,
                audience_value=next_audience_value,
            )
        )
        self.session.flush()
        return self.get_for_admin(announcement.id, org_id)

    def get_for_admin(self, announcement_id: int, org_id: int) -> Announcement | None:
        stmt = (
            select(Announcement)
            .options(selectinload(Announcement.audiences))
            .where(Announcement.id == announcement_id)
            .where(Announcement.org_id == org_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_for_admin(self, org_id: int) -> Sequence[Announcement]:
        stmt = (
            select(Announcement)
            .options(selectinload(Announcement.audiences))
            .where(Announcement.org_id == org_id)
            .order_by(Announcement.created_at.desc(), Announcement.id.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def update(
        self,
        *,
        announcement_id: int,
        org_id: int,
        title: str | None = None,
        body: str | None = None,
        audience_type: str | None = None,
        audience_value: str | None = None,
        status: str | None = None,
    ) -> Announcement | None:
        announcement = self.get_for_admin(announcement_id, org_id)
        if not announcement:
            return None

        if title is not None:
            if not title.strip():
                raise ValueError("title is required")
            announcement.title = title.strip()
        if body is not None:
            if not body.strip():
                raise ValueError("body is required")
            announcement.body = body.strip()
        if status is not None:
            next_status = self._validate_status(status)
            if announcement.status != next_status:
                announcement.status = next_status
                if next_status == "published" and not announcement.published_at:
                    announcement.published_at = datetime.now(timezone.utc)
                if next_status == "archived":
                    announcement.archived_at = datetime.now(timezone.utc)
                elif announcement.archived_at:
                    announcement.archived_at = None

        if audience_type is not None:
            next_type, next_value = self._validate_audience(audience_type, audience_value)
            for audience in list(announcement.audiences):
                self.session.delete(audience)
            self.session.flush()
            self.session.add(
                AnnouncementAudience(
                    announcement_id=announcement.id,
                    org_id=org_id,
                    audience_type=next_type,
                    audience_value=next_value,
                )
            )

        self.session.flush()
        return self.get_for_admin(announcement_id, org_id)

    def delete(self, announcement_id: int, org_id: int) -> bool:
        announcement = self.get_for_admin(announcement_id, org_id)
        if not announcement:
            return False
        self.session.delete(announcement)
        self.session.flush()
        return True

    def list_for_user(
        self,
        *,
        user_id: str,
        org_id: int,
        role: str,
        category_scope: str | None = None,
    ) -> list[dict]:
        audience_match = or_(
            AnnouncementAudience.audience_type == "all",
            and_(AnnouncementAudience.audience_type == "role", AnnouncementAudience.audience_value == role),
            and_(
                AnnouncementAudience.audience_type == "category",
                AnnouncementAudience.audience_value == (category_scope or ""),
            ),
            and_(AnnouncementAudience.audience_type == "user", AnnouncementAudience.audience_value == user_id),
        )
        stmt = (
            select(Announcement, AnnouncementReadState)
            .join(AnnouncementAudience, AnnouncementAudience.announcement_id == Announcement.id)
            .outerjoin(
                AnnouncementReadState,
                and_(
                    AnnouncementReadState.announcement_id == Announcement.id,
                    AnnouncementReadState.user_id == user_id,
                    AnnouncementReadState.org_id == org_id,
                ),
            )
            .options(selectinload(Announcement.audiences))
            .where(Announcement.org_id == org_id)
            .where(Announcement.status == "published")
            .where(audience_match)
            .order_by(Announcement.published_at.desc().nullslast(), Announcement.created_at.desc())
        )
        rows = self.session.execute(stmt).unique().all()
        return [
            announcement.to_dict(is_read=read_state is not None, read_at=read_state.read_at if read_state else None)
            for announcement, read_state in rows
        ]

    def mark_read(self, *, announcement_id: int, user_id: str, org_id: int) -> AnnouncementReadState:
        existing = self.session.execute(
            select(AnnouncementReadState)
            .where(AnnouncementReadState.announcement_id == announcement_id)
            .where(AnnouncementReadState.user_id == user_id)
            .where(AnnouncementReadState.org_id == org_id)
        ).scalar_one_or_none()
        if existing:
            return existing
        state = AnnouncementReadState(
            announcement_id=announcement_id,
            user_id=user_id,
            org_id=org_id,
            read_at=datetime.now(timezone.utc),
        )
        self.session.add(state)
        self.session.flush()
        return state
