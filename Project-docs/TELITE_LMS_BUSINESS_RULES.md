# TELITE LMS Business Rules

## 1. Ownership & Tenancy
- **Organization Boundary (Multi-Tenancy)**: Data is partitioned by Tenant ID. Organizations own branding, categories, and users.
- **Rule**: A user belongs to one or more organizations via the `Membership` model. Cross-tenant data access is strictly prohibited.
- **Verification**: `TenantMixin` implies that the tenant_id is enforced at the DB level, though ORM queries need to ensure filters are applied.

## 2. Uniqueness
- **User Identity**: Email addresses must be unique globally, but user roles/permissions are scoped to the organization.
- **Course Slugs**: Course slugs are unique within an organization, not globally.
- **Rule**: An organization cannot have two courses with the same slug.

## 3. Enrollment
- **Enrollment Flow**: Users request enrollment via `EnrollmentRequest`. Enrollment can be auto-approved or require manual review based on `ProgressionRule`.
- **Rule**: A user cannot start a course until the enrollment status is 'ACTIVE'.
- **Verification**: The `Enrollment` model tracks status.

## 4. Publishing & Visibility
- **Course Status**: Courses have states (Draft, Published, Archived).
- **Rule**: Only Published courses are visible to learners.
- **Course Versions**: `CourseVersion` allows editing a draft without affecting the published version.
- **Rule**: Editing an active course creates a new `CourseEditLock` to prevent concurrent modifications.

## 5. Learning Paths & Progression
- **Learning Path Structure**: A `LearningPath` aggregates multiple `LearningPathCourse` entries.
- **Rule**: Learners must complete courses in the order specified by the path if `ProgressionRule` enforces strict sequencing.
- **Progress Tracking**: `CourseProgress`, `ModuleProgress`, and `LessonBlockProgress` track granular completion.

## 6. Assessments & Grading
- **Quiz Attempts**: Users can have multiple `QuizAttempt` records.
- **Rule**: The final score is determined by the `GradingScheme` (Highest, Latest, Average).
- **Question Bank**: `QuestionBank` stores questions that can be reused across quizzes via `QuestionTagMap`.

## 7. Certificates
- **Issuance**: `Certificate` is issued upon meeting `CompletionRule` criteria.
- **Rule**: Certificates are immutable once issued; recalculating grades does not revoke a certificate unless specified by compliance rules.

## 8. Notifications
- **Event Triggers**: System events trigger `Notification` via `AnnouncementAudience`.
- **Rule**: Users only receive notifications for courses/paths they are enrolled in or global organization announcements.
