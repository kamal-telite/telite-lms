"""Audit Logging Service."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


class AuditService:
    @staticmethod
    def _actor_name(db: Session, user_id: str) -> str:
        if not user_id:
            return "System"
        user = db.query(User).filter(User.id == user_id).first()
        return user.full_name if user else str(user_id)

    @staticmethod
    def log(
        db: Session,
        org_id: int,
        user_id: str,
        entity_type: str,
        entity_id: str | int,
        action: str,
        course_id: str | None = None,
        before_dict: dict | None = None,
        after_dict: dict | None = None
    ) -> AuditLog:
        """
        Record a tenant audit log event.

        `audit_log` is the canonical persisted table. Course/before/after
        details are stored as metadata because the canonical table is shared
        across platform, builder, publishing, and media events.
        """
        metadata = {}
        if course_id is not None:
            metadata["course_id"] = course_id
        if before_dict is not None:
            metadata["before_json"] = before_dict
        if after_dict is not None:
            metadata["after_json"] = after_dict

        target_type = str(entity_type or "record").lower()
        target_id = str(entity_id)
        message = f"{action} {target_type} {target_id}".strip()

        log_entry = AuditLog(
            org_id=org_id,
            actor_user_id=user_id,
            actor_name=AuditService._actor_name(db, user_id),
            action=action,
            target_type=target_type,
            target_id=target_id,
            message=message,
            result="success",
            metadata_json=json.dumps(metadata, default=str) if metadata else None,
        )
        db.add(log_entry)
        db.flush()
        return log_entry
