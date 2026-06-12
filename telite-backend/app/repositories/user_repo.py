"""
UserRepository — all user data access operations.

Replaces the user-related functions in store.py:
fetch_user_by_id, fetch_user_by_identifier, list_users,
list_admins, create_or_update_admin, update_user_role,
set_user_active, soft_delete_user, update_user_moodle_id, etc.
"""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import or_, select, update

from app.models.user import User
from app.models.membership import Membership
from app.repositories.base_repo import BaseRepository
from app.core.utils import slugify, initials
from app.core.password_utils import hash_password

def role_gradients(role: str | None) -> tuple[str, str]:
    if role == "super_admin":
        return ("from-violet-600 to-indigo-600", "text-white")
    if role == "category_admin":
        return ("from-blue-600 to-cyan-600", "text-white")
    if role == "instructor":
        return ("from-emerald-600 to-teal-600", "text-white")
    if role == "reviewer":
        return ("from-amber-500 to-orange-500", "text-white")
    if role in ("learner", "student"):
        return ("from-slate-100 to-slate-200", "text-slate-800")
    return ("from-slate-100 to-slate-200", "text-slate-800")

class UserRepository(BaseRepository[User]):
    model = User

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username.lower().strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_identifier(self, identifier: str, *, include_hash: bool = False) -> User | None:
        """Find user by email or username."""
        ident = identifier.strip().lower()
        stmt = select(User).where(
            or_(User.email == ident, User.username == ident)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_platform_admin(self) -> User | None:
        stmt = select(User).where(User.is_platform_admin.is_(True)).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    # ── Org-scoped queries ────────────────────────────────────────────────────

    def list_by_org(
        self,
        org_id: int,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[User]:
        stmt = select(User).where(User.org_id == org_id)

        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search:
            term = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(term),
                    User.email.ilike(term),
                    User.username.ilike(term),
                )
            )

        stmt = stmt.order_by(User.full_name).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def list_admins_by_org(self, org_id: int) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.org_id == org_id)
            .where(User.role.in_(["super_admin", "category_admin"]))
            .where(User.is_active.is_(True))
            .order_by(User.full_name)
        )
        return self.session.execute(stmt).scalars().all()

    def count_active_learners(self, org_id: int | None = None) -> int:
        stmt = select(User).where(User.role == "learner").where(User.is_active.is_(True))
        if org_id is not None:
            stmt = stmt.where(User.org_id == org_id)
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return self.session.execute(count_stmt).scalar_one()

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_user(
        self,
        *,
        email: str,
        full_name: str,
        role: str,
        org_id: int,
        password: str,
        category_scope: str | None = None,
        username: str | None = None,
        is_platform_admin: bool = False,
        **extra: Any,
    ) -> User:
        """Create a new user with hashed password."""
        email = email.lower().strip()
        if username is None:
            username = self._build_unique_username(email, full_name)

        grad_start, grad_end = role_gradients(role)
        user = User(
            id=f"user-{uuid.uuid4().hex[:12]}",
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            category_scope=category_scope,
            password_hash=hash_password(password),
            avatar_initials=initials(full_name),
            gradient_start=grad_start,
            gradient_end=grad_end,
            is_active=True,
            is_platform_admin=is_platform_admin,
            status="active",
            org_id=org_id,
            organization_id=org_id,
            **extra,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def update_password(self, user: User, new_password: str) -> User:
        user.password_hash = hash_password(new_password)
        self.session.flush()
        return user

    def set_active(self, user: User, *, is_active: bool) -> User:
        user.is_active = is_active
        user.status = "active" if is_active else "suspended"
        self.session.flush()
        return user

    def update_role(self, user: User, *, role: str, category_scope: str | None = None) -> User:
        user.role = role
        user.category_scope = category_scope
        grad_start, grad_end = role_gradients(role)
        user.gradient_start = grad_start
        user.gradient_end = grad_end
        self.session.flush()
        return user



    def update_last_login(self, user_id: str, timestamp: str) -> None:
        self.session.execute(
            update(User).where(User.id == user_id).values(last_login=timestamp)
        )

    # ── Membership helpers ────────────────────────────────────────────────────

    def get_memberships(self, user_id: str) -> Sequence[Membership]:
        """Get all org memberships for a user (multi-org support)."""
        stmt = (
            select(Membership)
            .where(Membership.user_id == user_id)
            .where(Membership.status == "active")
        )
        return self.session.execute(stmt).scalars().all()

    def upsert_membership(
        self,
        *,
        user_id: str,
        org_id: int,
        role: str,
        category_scope: str | None = None,
        granted_by: str | None = None,
    ) -> Membership:
        """Create or update a user's membership in an organisation."""
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.org_id == org_id,
        )
        membership = self.session.execute(stmt).scalar_one_or_none()

        if membership is None:
            membership = Membership(
                user_id=user_id,
                org_id=org_id,
                role=role,
                category_scope=category_scope,
                status="active",
                granted_by=granted_by,
            )
            self.session.add(membership)
        else:
            membership.role = role
            membership.category_scope = category_scope
            membership.status = "active"

        self.session.flush()
        return membership

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_unique_username(self, email: str, full_name: str) -> str:
        base = slugify(email.split("@")[0]) or slugify(full_name) or "user"
        username = base
        counter = 1
        while self.get_by_username(username) is not None:
            username = f"{base}{counter}"
            counter += 1
        return username

def fetch_user_by_id(user_id: str) -> User | None:
    from app.db.engine import get_db_session
    with get_db_session() as session:
        return UserRepository(session).get_by_id(user_id)
