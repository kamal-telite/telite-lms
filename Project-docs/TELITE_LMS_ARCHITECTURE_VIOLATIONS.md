# TELITE LMS Architecture Violations

## 1. Tight Coupling
- **Observation**: `main.py` is quite large (15.7 KB) and likely contains routing and initialization logic that should be decoupled into smaller routers.
- **Violation**: Monolithic entry point contradicts layered architecture principles.

## 2. Inconsistent Ownership and Tenancy
- **Observation**: While `TenantMixin` exists, some audit or global tables like `PlatformSetting` or `AuditLog` might not clearly separate tenant boundaries vs system boundaries.
- **Violation**: Potential risk of cross-tenant data leakage if global settings are confused with tenant settings.

## 3. Circular Dependencies Risk
- **Observation**: `app/models/__init__.py` imports all models. With models like `TaskAssignment`, `TaskSubmission`, `TaskReview`, and `Course`, `Enrollment`, there's a high risk of circular imports if not carefully managed with late imports or string-based relationships.
- **Violation**: The ORM graph might become too tangled, making it hard to extract domains (e.g., separating Grading from Course Content).

## 4. Missing Aggregate Roots / Domain Boundaries
- **Observation**: The `models` directory contains 56 flat files. There are no clear module boundaries (e.g., `learning`, `assessments`, `billing`, `identity`).
- **Violation**: Flat structure in models indicates a data-driven architecture rather than domain-driven design, leading to a "Big Ball of Mud" over time.

## 5. Redundant Logic
- **Observation**: Multiple progress tracking models (`CourseProgress`, `ModuleProgress`, `LessonBlockProgress`, `LearningPathProgress`).
- **Violation**: High risk of synchronization issues. Updating a lesson block progress likely requires cascading updates up to the learning path progress, leading to complex state management and redundant DB writes.

## 6. Schema Inconsistencies
- **Observation**: Mixed naming conventions in models (e.g., `audit.py` vs `audit_log.py`, `builder_activity_log.py` vs `learner_activity_log.py`).
- **Violation**: Lack of naming consistency makes it harder to discover related logs and audit trails.
