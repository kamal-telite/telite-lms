"""Platform-level analytics queries."""

from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.models.session import AuthSession
from app.models.audit import AuditLog
from app.repositories.analytics.utils import iso_format


def get_platform_overview(session: Session) -> dict:
    """Return the strict platform overview contract consumed by admin UI."""
    total_orgs = session.execute(select(func.count(Organization.id))).scalar() or 0
    total_users = session.execute(select(func.count(User.id))).scalar() or 0
    active_sessions = (
        session.execute(
            select(func.count(AuthSession.id)).where(AuthSession.revoked_at.is_(None))
        ).scalar()
        or 0
    )
    recent_events = (
        session.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(10))
        .scalars()
        .all()
    )

    return {
        "total_orgs": total_orgs,
        "total_users": total_users,
        "active_sessions": active_sessions,
        "recent_activity": [
            {
                "id": event.id,
                "action": event.action,
                "actor_name": event.actor_name,
                "message": event.message,
                "created_at": iso_format(event.created_at),
                "org_id": event.org_id,
            }
            for event in recent_events
        ],
    }
