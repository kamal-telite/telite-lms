"""Audit Logging Service."""

from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

class AuditService:
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
        Record a granular audit log event.
        """
        log_entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            course_id=course_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            before_json=before_dict,
            after_json=after_dict
        )
        db.add(log_entry)
        db.flush()
        return log_entry
