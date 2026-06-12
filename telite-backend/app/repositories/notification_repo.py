"""
NotificationRepository — notification data access.

Replaces: list_notifications, mark_notifications_read,
_insert_notification, list_platform_notifications.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from sqlalchemy import select, update

from app.models.notification import Notification
from app.repositories.base_repo import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def list_for_user(
        self,
        user_id: str,
        org_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Sequence[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.org_id == org_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        return self.session.execute(stmt).scalars().all()

    def create(
        self,
        *,
        user_id: str,
        org_id: int,
        title: str,
        body: str,
        notif_type: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            org_id=org_id,
            title=title,
            body=body,
            type=notif_type,
            is_read=False,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.session.add(notif)
        self.session.flush()
        return notif

    def mark_read(self, user_id: str, org_id: int, notif_ids: list[int] | None = None) -> int:
        """Mark notifications as read. Pass notif_ids=None to mark all."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.org_id == org_id)
            .where(Notification.is_read.is_(False))
        )
        if notif_ids:
            stmt = stmt.where(Notification.id.in_(notif_ids))
        result = self.session.execute(stmt.values(is_read=True))
        return result.rowcount

    def count_unread(self, user_id: str, org_id: int) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.org_id == org_id)
            .where(Notification.is_read.is_(False))
        )
        return self.session.execute(stmt).scalar_one()
