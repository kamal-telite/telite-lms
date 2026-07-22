# TELITE LMS Feature Inventory

## 1. Authentication & Authorization
* **Purpose**: Manages user signups, logins, sessions, passwords, and API token generation.
* **Current Status**: Implemented
* **Owner Entity**: Auth Module
* **Primary Tables**: `user.py`, `session.py`, `password_reset_token.py`, `invitation.py`
* **Primary APIs**: `auth.py`, `signup.py`, `sessions.py`
* **Frontend Screens**: `src/pages/auth/*`, `src/pages/landing/*`
* **Services/Repositories**: Auth services, User repository, Session repository
* **Background Jobs**: Token cleanup (implied)
* **Dependencies**: None (Core system)

## 2. Organization Management
* **Purpose**: Manages tenants (companies/organizations), platform settings, and domain logic.
* **Current Status**: Implemented
* **Owner Entity**: Platform Admin / Organization Module
* **Primary Tables**: `organization.py`, `allowed_domain.py`, `platform_setting.py`
* **Primary APIs**: `platform.py`, `management.py`
* **Frontend Screens**: `src/pages/platform-admin/*`, `src/pages/super-admin/*`
* **Services/Repositories**: Organization service
* **Background Jobs**: None
* **Dependencies**: Authentication

## 3. User, Role & Permissions Management
* **Purpose**: Manages members within organizations, assigning roles and evaluating access permissions.
* **Current Status**: Implemented
* **Owner Entity**: Management / Permissions Module
* **Primary Tables**: `role_permission.py`, `membership.py`, `user.py`
* **Primary APIs**: `permissions.py`, `management.py`
* **Frontend Screens**: `src/pages/company/*`
* **Services/Repositories**: Permissions service, Membership service
* **Background Jobs**: None
* **Dependencies**: Authentication, Organization Management

## 4. Course Authoring & Builder
* **Purpose**: Enables creators to build courses, modules, sections, and lesson blocks. Supports versioning and locking.
* **Current Status**: Implemented
* **Owner Entity**: Authoring Module
* **Primary Tables**: `course.py`, `course_module.py`, `course_section.py`, `lesson_block.py`, `course_version.py`, `course_edit_lock.py`
* **Primary APIs**: `authoring.py`, `builder.py`, `publishing.py`
* **Frontend Screens**: `src/pages/authoring/*`
* **Services/Repositories**: Course builder service, Publishing service
* **Background Jobs**: Course publishing tasks
* **Dependencies**: User Management, Media Management

## 5. Media & Asset Management
* **Purpose**: Handles uploads, storage, and tracking of media assets used in courses and branding.
* **Current Status**: Implemented
* **Owner Entity**: Media Module
* **Primary Tables**: `media_asset.py`, `media_asset_usage.py`
* **Primary APIs**: `media.py`
* **Frontend Screens**: Shared asset library components
* **Services/Repositories**: Storage service (S3/Local)
* **Background Jobs**: Orphaned asset cleanup
* **Dependencies**: Authentication

## 6. Question Bank
* **Purpose**: Central repository for questions categorized and tagged for use in quizzes and assessments.
* **Current Status**: Implemented
* **Owner Entity**: Question Bank Module
* **Primary Tables**: `question.py`, `question_bank.py`, `question_category.py`, `question_tag.py`, `question_import_job.py`
* **Primary APIs**: `question_bank.py`
* **Frontend Screens**: `src/pages/authoring/*` (Question Bank section)
* **Services/Repositories**: Question service
* **Background Jobs**: Background question import jobs
* **Dependencies**: Authoring, Media Management

## 7. Quizzes & Assessments
* **Purpose**: Allows authoring and execution of quizzes, tracking attempts and answers.
* **Current Status**: Implemented
* **Owner Entity**: Quiz Module
* **Primary Tables**: `quiz_models.py`, `quiz_attempt.py`, `quiz_answer.py`
* **Primary APIs**: `quiz_authoring.py`, `quiz_execution.py`, `quiz_grading.py`
* **Frontend Screens**: `src/pages/learner/*` (Quiz player), `src/pages/authoring/*` (Quiz builder)
* **Services/Repositories**: Quiz execution service, Auto-grading service
* **Background Jobs**: None
* **Dependencies**: Question Bank, Course Authoring

## 8. Assignments & Gradebook
* **Purpose**: Manages assignment submissions, manual grading, rubrics, and the overall gradebook for learners.
* **Current Status**: Implemented
* **Owner Entity**: Grading Module
* **Primary Tables**: `assignment_submission.py`, `gradebook.py`, `rubric.py`
* **Primary APIs**: `assignments.py`, `gradebook.py`
* **Frontend Screens**: `src/pages/company/*` (Instructor view), `src/pages/learner/*` (Grades view)
* **Services/Repositories**: Grading service
* **Background Jobs**: None
* **Dependencies**: Course Authoring, User Management

## 9. Learning Paths
* **Purpose**: Groups courses into structured paths for sequential or guided learning.
* **Current Status**: Implemented
* **Owner Entity**: Learning Paths Module
* **Primary Tables**: `learning_path.py`, `progression_rule.py`
* **Primary APIs**: `learning_paths.py`
* **Frontend Screens**: `src/pages/company/*`, `src/pages/learner/*`
* **Services/Repositories**: Learning path service
* **Background Jobs**: None
* **Dependencies**: Course Authoring

## 10. Learner Player & Dashboard
* **Purpose**: The primary interface where learners discover, enroll, and consume course content.
* **Current Status**: Implemented
* **Owner Entity**: Learner Module
* **Primary Tables**: `enrollment.py`, `learner_event.py`, `course_review.py`
* **Primary APIs**: `learner.py`, `player_api.py`, `enrolments.py`, `dashboard.py`
* **Frontend Screens**: `src/pages/learner/*`
* **Services/Repositories**: Learner service, Enrollment service
* **Background Jobs**: None
* **Dependencies**: Auth, Course Authoring, Learning Paths

## 11. Progress Tracking
* **Purpose**: Tracks granular progression through paths, courses, modules, sections, and blocks.
* **Current Status**: Implemented
* **Owner Entity**: Progress Module
* **Primary Tables**: `learning_path_progress.py`, `course_progress.py`, `module_progress.py`, `section_progress.py`, `lesson_block_progress.py`, `interactive_tracking.py`
* **Primary APIs**: `player_api.py`, `learner.py`
* **Frontend Screens**: Learner Dashboard & Player widgets
* **Services/Repositories**: Progress service
* **Background Jobs**: Progress aggregation
* **Dependencies**: Learner Player

## 12. Certificates
* **Purpose**: Generates and awards certificates upon course or path completion.
* **Current Status**: Implemented
* **Owner Entity**: Certificate Module
* **Primary Tables**: `certificate.py`
* **Primary APIs**: `certificates.py`
* **Frontend Screens**: Learner certificate view
* **Services/Repositories**: Certificate generation service (PDF rendering)
* **Background Jobs**: Async certificate generation
* **Dependencies**: Progress Tracking

## 13. Custom Branding
* **Purpose**: Customizes platform look and feel for different organizations.
* **Current Status**: Implemented
* **Owner Entity**: Branding Module
* **Primary Tables**: `branding.py`, `organization_branding.py`
* **Primary APIs**: `branding.py`, `admin_branding.py`
* **Frontend Screens**: Custom CSS/theme providers
* **Services/Repositories**: Branding service
* **Background Jobs**: None
* **Dependencies**: Organization Management

## 14. Notifications & Announcements
* **Purpose**: Broadcasts messages to users and triggers alerts for events (enrollment, grading, etc.).
* **Current Status**: Implemented
* **Owner Entity**: Communications Module
* **Primary Tables**: `notification.py`, `announcement.py`
* **Primary APIs**: `notifications.py`, `announcements.py`
* **Frontend Screens**: Notification bell/center in all layouts
* **Services/Repositories**: Notification dispatcher
* **Background Jobs**: Async email/push notification delivery
* **Dependencies**: All core modules (event sources)

## 15. Tasks & Workflows
* **Purpose**: Manages asynchronous or manual tasks and approval workflows within the system.
* **Current Status**: Implemented
* **Owner Entity**: Workflow Module
* **Primary Tables**: `task.py`, `task_workflow.py`
* **Primary APIs**: `tasks.py`
* **Frontend Screens**: Task inbox (Company/Admin)
* **Services/Repositories**: Workflow engine
* **Background Jobs**: Task state evaluation
* **Dependencies**: Organization, User Management

## 16. PAL (Predictive/Personal AI Learning)
* **Purpose**: AI-driven features for recommendations or assistance.
* **Current Status**: Implemented
* **Owner Entity**: AI Module
* **Primary Tables**: `pal.py`
* **Primary APIs**: `pal.py`
* **Frontend Screens**: AI Assistant UI components
* **Services/Repositories**: AI integration service
* **Background Jobs**: AI background processing
* **Dependencies**: User Data, Progress Tracking

## 17. Auditing & Logging
* **Purpose**: Maintains compliance and security logs of system activities by builders and learners.
* **Current Status**: Implemented
* **Owner Entity**: Audit Module
* **Primary Tables**: `audit.py`, `audit_log.py`, `builder_activity_log.py`, `learner_activity_log.py`
* **Primary APIs**: `audit.py`
* **Frontend Screens**: Admin Audit logs view
* **Services/Repositories**: Audit logging service
* **Background Jobs**: Log archiving
* **Dependencies**: System-wide

## 18. Payments
* **Purpose**: Handles transactions for paid content.
* **Current Status**: Implemented
* **Owner Entity**: Commerce Module
* **Primary Tables**: `pending_verification.py` (and potentially external payment references)
* **Primary APIs**: `payments.py`
* **Frontend Screens**: Checkout flow
* **Services/Repositories**: Payment gateway integration
* **Background Jobs**: Payment verification webhooks
* **Dependencies**: User Management, Course Authoring
