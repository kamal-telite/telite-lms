# ADR 002: Polymorphic Referential Integrity for Progression Rules

**Status:** Proposed
**Context:** The `progression_rules` table dynamically targets either `course_modules` or `course_sections` using a `(target_type, target_id)` composite pattern. The original database migration incorrectly attempted to enforce this via two concurrent PostgreSQL `FOREIGN KEY` constraints on the same `target_id` column. This requires resolution to establish a canonical and stable architecture.

## Options Analyzed

### Option A: Exclusive Arcs (Database Normalization)
Redesign the schema to use explicit, nullable foreign keys for every possible target type (`module_id`, `section_id`), constrained by a database `CHECK` rule ensuring exactly one is populated.

- **Data Integrity:** High. PostgreSQL strictly enforces relationships and native `ON DELETE CASCADE`.
- **Migration Complexity:** High. Requires schema migrations, data translation, and significant refactoring of ORM and API repositories.
- **Performance:** Excellent for joins. No dynamic queries required.
- **Compatibility:** Breaks the existing `target_type/target_id` paradigm. Requires compatibility shims at the API layer.
- **Future Roadmap:** Poor. Adding new progression targets (e.g., `Course`, `Lesson`, `Quiz`, `Assignment`) requires new database migrations to add columns and modify the `CHECK` constraint.

### Option B: Application-Enforced Polymorphism (Current Paradigm)
Retain the generic `(target_type, target_id)` columns, remove the invalid PostgreSQL foreign key constraints, and enforce referential integrity entirely within the application layer.

- **Data Integrity:** Enforced by application logic (SQLAlchemy). Database allows orphans if bypassed.
- **Migration Complexity:** Extremely low. Simply drop the invalid constraints. Zero changes required to Repositories, APIs, or business logic.
- **Performance:** Good. Requires separate queries for different target types, but this matches the existing service pattern.
- **Compatibility:** 100% compatible with existing API and repository code.
- **Future Roadmap:** Excellent. Highly extensible. Adding a rule for a new target type (e.g., `target_type="lesson"`) requires zero database schema changes.

### Option C: Database Triggers (Polymorphic DB Enforcement)
Retain `(target_type, target_id)` but use custom PostgreSQL `pl/pgsql` triggers to dynamically validate existence based on `target_type`.

- **Data Integrity:** High. Enforced at the DB level.
- **Migration Complexity:** High. Writing and maintaining custom trigger logic for standard CRUD operations is brittle.
- **Compatibility:** Preserves ORM design.
- **Developer Ergonomics:** Terrible. Obscures business logic inside the database layer, invisible to the ORM.

## Recommendation

**Option B (Application-Enforced Polymorphism)** is the recommended architecture for TELITE's long-term design.

### Justification

1. **Industry Standard Extensibility:** The `(target_type, target_id)` pattern (often called Generic Foreign Keys or Polymorphic Associations) is the standard architectural choice in modern ORM-driven frameworks (Django, Rails) precisely because it decouples rule configuration from schema migrations. An LMS will inevitably require progression rules for Courses, Lessons, Quizzes, and Assignments. Option B supports this infinite extensibility with zero database friction.
2. **Soft Deletion Reality:** TELITE relies on Soft Deletes (`deleted_at`). PostgreSQL `ON DELETE CASCADE` constraints are bypassed by soft deletes anyway because the row is `UPDATE`d, not `DELETE`d. Therefore, referential integrity for deleted targets *must* already be enforced by the application layer. 
3. **Low Risk:** Attempting to force Option A would introduce immediate, heavy refactoring risk across the API and repository layers to solve a problem (cascading deletes) that soft-deletes already prevent the database from solving automatically.

## Architectural Principle Clarification

It is critical to explicitly state that this decision is **an exception for polymorphic associations only**.

- Normal relational entities within the TELITE system **must** continue using strict database-level foreign key constraints whenever practical.
- Application-enforced referential integrity is strictly reserved for edge cases where a single reference (e.g., `target_id`) legitimately targets multiple entity types and therefore cannot be modeled cleanly with conventional relational database constraints.
- This ADR must not be interpreted as a general recommendation or precedent to replace database foreign keys throughout the broader system architecture.

## Consequences
- We accept that hard-deleting a module or section directly via SQL could leave orphaned `progression_rules`.
- Application logic must continue validating `target_id` existence before creation.
- We proceed with **Package 3** by dropping the two physical PostgreSQL `FOREIGN KEY` constraints on `target_id`, and removing the ORM `ForeignKeyConstraint` declaration.
