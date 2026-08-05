"""
NotificationRepository — notification data access.

Replaces: list_notifications, mark_notifications_read,
_insert_notification, list_platform_notifications.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.core.notification_payloads import ACTIVE_NOTIFICATION_TYPES, validate_notification_payload
from app.core.observability import log_background_task_failure
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("telite.notifications")


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
        message: str,
        notif_type: str = "info",
        metadata: dict[str, Any] | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
    ) -> Notification:
        try:
            notif_type_value = getattr(notif_type, "value", notif_type)
            source_id_value = str(source_id) if source_id is not None else None
            if notif_type_value in ACTIVE_NOTIFICATION_TYPES:
                if not source_type or source_id is None:
                    raise ValueError("active notification producers must include source_type and source_id")
                validate_notification_payload(metadata)
            notif = Notification(
                user_id=user_id,
                org_id=org_id,
                title=title,
                body=message,
                type=notif_type_value,
                is_read=False,
                metadata_json=json.dumps(metadata) if metadata else None,
                source_type=source_type,
                source_id=source_id_value,
            )
            self.session.add(notif)
            self.session.flush()
            return notif
        except Exception as exc:
            log_background_task_failure(
                task_name="notification_creation",
                exception=exc,
                context={
                    "user_id": user_id,
                    "org_id": org_id,
                    "notif_type": notif_type,
                    "source_type": source_type,
                },
            )
            raise

    def create_once(
        self,
        *,
        user_id: str,
        org_id: int,
        title: str,
        message: str,
        notif_type: str,
        idempotency_key: str,
        metadata: dict[str, Any],
        source_type: str,
        source_id: str,
    ) -> Notification:
        notif_type_value = getattr(notif_type, "value", notif_type)
        source_id_value = str(source_id)
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.org_id == org_id)
            .where(Notification.type == notif_type_value)
            .where(Notification.source_type == source_type)
            .where(Notification.source_id == source_id_value)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
        for existing in self.session.execute(stmt).scalars().all():
            if existing.metadata_payload().get("idempotency_key") == idempotency_key:
                return existing

        next_metadata = dict(metadata)
        next_metadata["idempotency_key"] = idempotency_key
        return self.create(
            user_id=user_id,
            org_id=org_id,
            title=title,
            message=message,
            notif_type=notif_type_value,
            metadata=next_metadata,
            source_type=source_type,
            source_id=source_id_value,
        )

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
