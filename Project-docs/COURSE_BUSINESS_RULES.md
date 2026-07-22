# Course Business Rules

## 1. Objective
Determine whether the architecture supports the rule: "Within a single Organization and Category, a Course Name must be unique" (e.g., allowing the same name in a different category or organization).

## 2. Findings
**The architecture DOES NOT support this rule.**

Currently, the architecture enforces a much stricter, global constraint that prevents a Course Name (specifically its generated slug) from being reused *anywhere* in the system, across all organizations and categories.

## 3. Root Cause Analysis
The inability to support scoped uniqueness (by Organization and Category) stems from a combination of the database schema definition and the course creation logic.

### Evidence 1: Global Unique Constraint (`app/models/course.py`)
The `Course` model defines the `slug` column with a global `unique=True` constraint:
```python
class Course(Base, TenantMixin, TimestampMixin):
    __tablename__ = "courses"
    # ...
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
```
This applies a unique index across the entire `courses` table. It is not scoped to `org_id` or `category_slug`.

### Evidence 2: Slug Generation (`app/repositories/course_repo.py`)
When a new course is created in `CourseRepository.create_course`, the `slug` is deterministically generated from the `name` if not explicitly provided:
```python
def create_course(self, *, name: str, category_slug: str, org_id: int, ...):
    slug = extra.pop("slug", None) or slugify(name)
```

### The Breaking Scenario
If Organization A creates a course named "Introduction to Math" in the "Science" category, the slug becomes `introduction-to-math`.
If Organization B (or even Organization A in a different category) attempts to create a course also named "Introduction to Math", the `slugify` function will generate the exact same slug: `introduction-to-math`.
Upon attempting to insert this record, SQLAlchemy and PostgreSQL will throw an `IntegrityError` due to the global unique constraint on the `slug` column.

## 4. Conclusion
To support the rule where "Course Name must be unique only within a single Organization and Category", the architecture must be modified:
1. The global `unique=True` constraint on `Course.slug` must be dropped.
2. A composite unique constraint must be added across `(org_id, category_slug, slug)` or `(org_id, category_slug, name)`.
