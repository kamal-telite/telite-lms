# RC-003 Resolution: Architecture Assessment

## The Bug: RC-003
RC-003 is characterized by course and category creation failures due to slug collisions across different organizations in the Telite LMS.

## Root Cause Analysis
An audit of the SQLAlchemy models in `app/models/course.py` and `app/models/category.py` revealed the architectural flaw:

```python
# In app/models/course.py
slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

# In app/models/category.py
slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
```

The `unique=True` constraint on the `slug` column creates a database-wide UNIQUE index. Because these tables inherit from `TenantMixin`, they are intended to be multi-tenant. However, the global uniqueness on the slug completely bypasses tenant isolation. 

When Organization A creates a course with the name "Advanced Mathematics" (generating slug `advanced-mathematics`), if Organization B subsequently attempts to create a course with the same name, the database rejects it with an IntegrityError, preventing multi-tenant scaling.

## The Architectural Fix
The canonical identity of a course must be redefined from **Global Slug** to **Tenant-Scoped Slug (`org_id + slug`)**.

### Why Not Category-Scoped?
We evaluated scoping by `category_slug` (`org_id + category_slug + slug`). However, checking `app/repositories/course_repo.py`, the `update_course` method permits altering the course's category. If uniqueness were scoped to the category, moving a course would alter its fundamental identity signature, causing complex downstream effects for bookmarks and tracking.

### Implementation Steps to Fix RC-003
1. Generate an Alembic migration to drop the global `slug` unique constraints.
2. Add a `UniqueConstraint('org_id', 'slug', name='uq_course_org_slug')` to the `courses` table.
3. Add a `UniqueConstraint('org_id', 'slug', name='uq_category_org_slug')` to the `categories` table.

By making `org_id + slug` the canonical identity, RC-003 is completely resolved, allowing infinite horizontal scaling of tenants with overlapping course names.
