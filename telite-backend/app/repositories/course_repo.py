"""
CourseRepository — course and category data access.

Replaces: list_courses, get_course, create_or_update_course,
archive_course, list_categories, get_category, create_category, etc.
"""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.course import Course
from app.repositories.base_repo import BaseRepository
from app.core.utils import slugify


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_slug(self, slug: str) -> Category | None:
        stmt = select(Category).where(Category.slug == slug.strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_org(
        self,
        org_id: int,
        *,
        include_archived: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Category]:
        stmt = select(Category).where(Category.org_id == org_id)
        if not include_archived:
            stmt = stmt.where(Category.status != "archived")
        stmt = stmt.order_by(Category.name).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def create_category(
        self,
        *,
        name: str,
        org_id: int,
        org_type: str = "college",
        description: str | None = None,
        accent_color: str = "#2563EB",
        admin_user_id: str | None = None,
        **extra: Any,
    ) -> Category:
        slug = extra.pop("slug", None) or slugify(name)
        cat = Category(
            id=f"cat-{uuid.uuid4().hex[:8]}",
            name=name.strip(),
            slug=slug,
            description=description,
            status="active",
            accent_color=accent_color,
            admin_user_id=admin_user_id,
            org_type=org_type,
            org_id=org_id,
            organization_id=org_id,
            **extra,
        )
        self.session.add(cat)
        self.session.flush()
        return cat

    def archive_category(self, category: Category, archived_at: str) -> Category:
        category.status = "archived"
        category.archived_at = archived_at
        self.session.flush()
        return category


class CourseRepository(BaseRepository[Course]):
    model = Course

    def get_by_slug(self, slug: str) -> Course | None:
        stmt = select(Course).where(Course.slug == slug.strip())
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_org(
        self,
        org_id: int,
        *,
        category_slug: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Course]:
        stmt = select(Course).where(Course.org_id == org_id)
        if category_slug:
            stmt = stmt.where(Course.category_slug == category_slug)
        if status:
            stmt = stmt.where(Course.status == status)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                or_(Course.name.ilike(term), Course.description.ilike(term))
            )
        stmt = stmt.order_by(Course.name).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def list_purchasable(self, org_id: int) -> Sequence[Course]:
        """List courses available for purchase (price_paise > 0)."""
        stmt = (
            select(Course)
            .where(Course.org_id == org_id)
            .where(Course.status == "active")
            .where(Course.price_paise > 0)
            .order_by(Course.name)
        )
        return self.session.execute(stmt).scalars().all()

    def create_course(
        self,
        *,
        name: str,
        category_slug: str,
        org_id: int,
        description: str = "",
        tier: str = "Basic",
        **extra: Any,
    ) -> Course:
        slug = extra.pop("slug", None) or slugify(name)
        course = Course(
            id=f"course-{uuid.uuid4().hex[:10]}",
            name=name.strip(),
            slug=slug,
            category_slug=category_slug,
            description=description,
            tier=tier,
            status="active",
            org_id=org_id,
            **extra,
        )
        self.session.add(course)
        self.session.flush()
        return course

    def update_course(self, course: Course, **fields: Any) -> Course:
        for key, value in fields.items():
            if hasattr(course, key):
                setattr(course, key, value)
        self.session.flush()
        return course

    def archive_course(self, course: Course) -> Course:
        course.status = "archived"
        self.session.flush()
        return course

