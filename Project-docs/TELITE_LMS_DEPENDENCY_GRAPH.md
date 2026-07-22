# TELITE LMS Dependency Graph

## Overview
This document maps the dependencies between core features, showing data flow and architectural coupling in the TELITE LMS system.

## 1. Authentication & Authorization
* **Depends On**: None (Root Dependency)
* **Depended On By**: Every other feature in the system.
* **Shared Components**: Auth middlewares, Session validation guards.
* **Shared Tables**: `user.py`, `session.py`

## 2. Organization Management
* **Depends On**: Authentication
* **Depended On By**: User Management, Course Authoring, Custom Branding, Tasks & Workflows
* **Shared Components**: Tenant resolution middleware
* **Shared Tables**: `organization.py`

## 3. User, Role & Permissions Management
* **Depends On**: Authentication, Organization Management
* **Depended On By**: Authoring, Learner Player, Grading, Auditing
* **Shared Components**: RBAC (Role-Based Access Control) decorators
* **Shared Tables**: `user.py`, `role_permission.py`, `membership.py`

## 4. Media & Asset Management
* **Depends On**: Authentication, Organization Management
* **Depended On By**: Course Authoring, Question Bank, Custom Branding
* **Shared Components**: File upload utilities, CDN URL generators
* **Shared Tables**: `media_asset.py`

## 5. Course Authoring & Builder
* **Depends On**: User Management, Media Management
* **Depended On By**: Learner Player, Learning Paths, Quizzes, Assignments, Progress Tracking
* **Shared Components**: Course structure definitions
* **Shared Tables**: `course.py`, `course_module.py`, `course_section.py`, `lesson_block.py`

## 6. Question Bank
* **Depends On**: Course Authoring, Media Management
* **Depended On By**: Quizzes & Assessments
* **Shared Components**: Question schemas and rich-text renderers
* **Shared Tables**: `question.py`, `question_bank.py`

## 7. Quizzes & Assessments
* **Depends On**: Question Bank, Course Authoring, Progress Tracking
* **Depended On By**: Gradebook, Learner Player
* **Shared Components**: Quiz Player UI, Auto-grading engine
* **Shared Tables**: `quiz_models.py`, `quiz_attempt.py`

## 8. Assignments & Gradebook
* **Depends On**: Course Authoring, User Management, Quizzes
* **Depended On By**: Certificates, Learner Dashboard
* **Shared Components**: Rubric evaluator
* **Shared Tables**: `gradebook.py`, `assignment_submission.py`

## 9. Learning Paths
* **Depends On**: Course Authoring
* **Depended On By**: Learner Player, Progress Tracking
* **Shared Components**: Path enrollment logic
* **Shared Tables**: `learning_path.py`

## 10. Learner Player & Dashboard
* **Depends On**: Course Authoring, Learning Paths, Quizzes, Assignments, User Management
* **Depended On By**: Progress Tracking, Auditing
* **Shared Components**: Course Consumption UI
* **Shared Tables**: `enrollment.py`

## 11. Progress Tracking
* **Depends On**: Learner Player, Course Authoring
* **Depended On By**: Certificates, Gradebook, PAL (AI)
* **Shared Components**: Event stream processors
* **Shared Tables**: `*_progress.py` tables

## 12. Certificates
* **Depends On**: Progress Tracking, Course Authoring, Gradebook
* **Depended On By**: Learner Dashboard
* **Shared Components**: PDF Generator
* **Shared Tables**: `certificate.py`

## 13. Custom Branding
* **Depends On**: Organization Management, Media Management
* **Depended On By**: Frontend UI Layouts
* **Shared Components**: Theme provider
* **Shared Tables**: `branding.py`

## 14. Notifications & Announcements
* **Depends On**: All Core Modules (acts as a sink for events)
* **Depended On By**: Frontend UI (Notification Bell)
* **Shared Components**: Event Dispatcher, Email Service
* **Shared Tables**: `notification.py`

## 15. Tasks & Workflows
* **Depends On**: User Management, Organization
* **Depended On By**: Administration screens
* **Shared Components**: State Machine Engine
* **Shared Tables**: `task.py`

## 16. PAL (Predictive AI)
* **Depends On**: Progress Tracking, Learner Player, User Data
* **Depended On By**: Dashboard Recommendations
* **Shared Components**: Inference client
* **Shared Tables**: `pal.py`

## 17. Auditing & Logging
* **Depends On**: System-wide components
* **Depended On By**: Admin Reports
* **Shared Components**: Audit interceptors/middlewares
* **Shared Tables**: `audit_log.py`

## 18. Payments
* **Depends On**: User Management, Course Authoring
* **Depended On By**: Learner Enrollment Process
* **Shared Components**: Stripe/Payment Gateway Client
* **Shared Tables**: `pending_verification.py`
