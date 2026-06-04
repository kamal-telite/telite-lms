"""
BaseRepository — shared query helpers for all repositories.

Every repository inherits from this class to get:
- Org-scoped queries (tenant isolation)
- Pagination helpers
- Soft-delete support
- Audit trail helpers
"""

from __future__ import annotations

import logging
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)
logger = logging.getLogger("telite.repositories")


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing org-scoped CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: Type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, record_id: Any) -> ModelT | None:
        """Fetch a single record by primary key."""
        return self.session.get(self.model, record_id)

    def get_by_id_and_org(self, record_id: Any, org_id: int) -> ModelT | None:
        """Fetch a record by PK, enforcing org ownership."""
        record = self.session.get(self.model, record_id)
        if record is None:
            return None
        # Check org_id if the model has it
        if hasattr(record, "org_id") and record.org_id != org_id:
            return None
        return record

    def list_by_org(
        self,
        org_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by=None,
    ) -> Sequence[ModelT]:
        """List all records for an organisation with pagination."""
        stmt = select(self.model).where(
            getattr(self.model, "org_id") == org_id
        )
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def count_by_org(self, org_id: int) -> int:
        """Count records for an organisation."""
        stmt = select(func.count()).select_from(self.model).where(
            getattr(self.model, "org_id") == org_id
        )
        return self.session.execute(stmt).scalar_one()

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new record."""
        record = self.model(**kwargs)
        self.session.add(record)
        self.session.flush()  # get PK without committing
        return record

    def update(self, record: ModelT, **kwargs: Any) -> ModelT:
        """Update fields on an existing record."""
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        self.session.flush()
        return record

    def delete(self, record: ModelT) -> None:
        """Hard delete a record."""
        self.session.delete(record)
        self.session.flush()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def exists(self, **filters: Any) -> bool:
        """Check if a record matching the filters exists."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return self.session.execute(stmt).scalar_one() > 0

    def paginate(
        self,
        stmt,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Apply pagination to a select statement and return metadata."""
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        offset = (page - 1) * page_size

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        # Fetch page
        items = self.session.execute(
            stmt.limit(page_size).offset(offset)
        ).scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }
