"""
AuthRepository — session and password reset token data access.

Replaces: create_session, get_session_by_token, revoke_session,
revoke_sessions_for_user, update_last_login, create_password_reset_token,
validate_password_reset_token, reset_password_with_token, etc.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.session import AuthSession
from app.repositories.base_repo import BaseRepository


class AuthRepository(BaseRepository[AuthSession]):
    model = AuthSession

    # ── Session management ────────────────────────────────────────────────────

    def get_by_token(self, refresh_token: str) -> AuthSession | None:
        stmt = (
            select(AuthSession)
            .where(AuthSession.refresh_token == refresh_token)
            .where(AuthSession.revoked_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_session(
        self,
        *,
        user_id: str,
        org_id: int,
        refresh_token: str,
        expires_at: str,
    ) -> AuthSession:
        session_record = AuthSession(
            id=f"sess-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            org_id=org_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        self.session.add(session_record)
        self.session.flush()
        return session_record

    def revoke_session(self, refresh_token: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.session.execute(
            update(AuthSession)
            .where(AuthSession.refresh_token == refresh_token)
            .values(revoked_at=now)
        )

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all active sessions for a user. Returns count revoked."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        result = self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id)
            .where(AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return result.rowcount

    def list_active_sessions(self, user_id: str) -> list[AuthSession]:
        stmt = (
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .where(AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count deleted."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        stmt = select(AuthSession).where(AuthSession.expires_at < now)
        expired = self.session.execute(stmt).scalars().all()
        count = len(expired)
        for s in expired:
            self.session.delete(s)
        self.session.flush()
        return count
