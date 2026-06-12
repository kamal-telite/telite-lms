"""
AuditRepository — audit log and activity log data access.

Replaces: _insert_audit, _insert_activity, list_audit_entries,
list_activity_entries, write_platform_audit, list_audit_logs, etc.
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select

from app.models.audit import ActivityLog, AuditLog
from app.repositories.base_repo import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def write(
        self,
        *,
        org_id: int,
        actor_user_id: str | None,
        actor_name: str,
        action: str,
        target_type: str,
        target_id: str,
        message: str,
        result: str = "success",
        accent: str = "#2563EB",
        severity: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        import json
        entry = AuditLog(
            org_id=org_id,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            message=message,
            result=result,
            accent=accent,
            severity=severity,
            ip_address=ip_address,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_by_org(
        self,
        org_id: int,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.org_id == org_id)
            .order_by(AuditLog.created_at.desc())
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_user_id == actor_id)
        stmt = stmt.limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()


class ActivityRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    def write(
        self,
        *,
        org_id: int,
        user_id: str | None,
        category_slug: str | None,
        icon: str,
        accent: str,
        message: str,
    ) -> ActivityLog:
        entry = ActivityLog(
            org_id=org_id,
            user_id=user_id,
            category_slug=category_slug,
            icon=icon,
            accent=accent,
            message=message,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_by_org(
        self,
        org_id: int,
        *,
        category_slug: str | None = None,
        limit: int = 50,
    ) -> Sequence[ActivityLog]:
        stmt = (
            select(ActivityLog)
            .where(ActivityLog.org_id == org_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
        if category_slug:
            stmt = stmt.where(ActivityLog.category_slug == category_slug)
        return self.session.execute(stmt).scalars().all()
