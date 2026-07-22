"""
CourseRepository — course and category data access.

Replaces: list_courses, get_course, create_or_update_course,
archive_course, list_categories, get_category, create_category, etc.
"""

from __future__ import annotations

import uuid
import json
from typing import Any, Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

class DuplicateResourceError(Exception):
    def __init__(self, resource_type: str, field: str, message: str):
        self.resource_type = resource_type
        self.field = field
        self.message = message
        super().__init__(self.message)

from app.models.category import Category
from app.models.course import Course
from app.repositories.base_repo import BaseRepository
from app.core.utils import slugify


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_slug(self, slug: str, org_id: int) -> Category | None:
        stmt = select(Category).where(Category.slug == slug.strip(), Category.org_id == org_id)
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

    def validate_category_creation(self, slug: str, org_id: int) -> None:
        if self.get_by_slug(slug, org_id):
            raise DuplicateResourceError(
                resource_type="category",
                field="name",
                message="Category name already exists."
            )

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
        name = name.strip()
        slug = extra.pop("slug", None)
        if not slug:
            slug = slugify(name)
        slug = slug.strip().lower()
        
        self.validate_category_creation(slug, org_id)

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
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateResourceError(
                resource_type="category",
                field="name",
                message="Category name already exists."
            )
        return cat

    def archive_category(self, category: Category, archived_at: str) -> Category:
        category.status = "archived"
        category.archived_at = archived_at
        self.session.flush()
        return category


class CourseRepository(BaseRepository[Course]):
    model = Course

    def get_by_slug(self, slug: str, org_id: int) -> Course | None:
        stmt = select(Course).where(Course.slug == slug.strip(), Course.org_id == org_id)
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

    def validate_course_creation(self, slug: str, org_id: int) -> None:
        if self.get_by_slug(slug, org_id):
            raise DuplicateResourceError(
                resource_type="course",
                field="name",
                message="Course name already exists."
            )

    def list_by_ids_for_org(self, course_ids: list[str], org_id: int) -> Sequence[Course]:
        if not course_ids:
            return []
        stmt = select(Course).where(
            Course.id.in_(course_ids),
            Course.org_id == org_id,
        )
        return self.session.execute(stmt).scalars().all()

    def list_purchasable(self, org_id: int) -> Sequence[Course]:
        """List courses available for purchase (price_paise > 0)."""
        stmt = (
            select(Course)
            .where(Course.org_id == org_id)
            .where(Course.status.in_(("active", "published")))
            .where(Course.status != "draft")
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
        name = name.strip()
        slug = extra.pop("slug", None)
        if not slug:
            slug = slugify(name)
        slug = slug.strip().lower()
        
        self.validate_course_creation(slug, org_id)

        status = extra.pop("status", "draft")
        modules = extra.pop("modules", None)
        modules_json = extra.pop("modules_json", None)
        if modules_json is None and modules is not None:
            modules_json = json.dumps(modules)
        course = Course(
            id=f"course-{uuid.uuid4().hex[:10]}",
            name=name.strip(),
            slug=slug,
            category_slug=category_slug,
            description=description,
            tier=tier,
            status=status,
            org_id=org_id,
            modules_json=modules_json or "[]",
            **extra,
        )
        self.session.add(course)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateResourceError(
                resource_type="course",
                field="name",
                message="Course name already exists."
            )
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

