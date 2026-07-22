# TELITE LMS Database Schema Audit

## Overview
This document contains an architecture audit of the TELITE LMS database models, derived from the repository structure in `telite-backend/app/models`.

## Table Analysis

### Organizations (`organizations`)
- **Primary Key**: `id`
- **Soft Delete**: `is_deleted`
- **Relationships**: Users, Categories, Settings.

### Categories (`categories`)
- **Primary Key**: `id`
- **Tenant Field**: `organization_id`
- **Relationships**: Courses, Organizations.

### Courses (`courses`)
- **Primary Key**: `id`
- **Tenant Field**: `organization_id`
- **Relationships**: Sections, Certificates, Reviews.

### Course Sections (`course_sections`)
- **Primary Key**: `id`
- **Relationships**: Course, Course Modules.

### Course Modules (`course_modules`)
- **Primary Key**: `id`
- **Relationships**: Section, Lesson Blocks.

### Lesson Blocks (`lesson_blocks`)
- **Primary Key**: `id`
- **Relationships**: Module, Assessments, Media.

### Enrollments (`enrollment_requests`)
- **Primary Key**: `id`
- **Relationships**: User, Course.

### Certificates (`certificates`)
- **Primary Key**: `id`
- **Relationships**: User, Course.

### Learning Paths (`learning_paths`)
- **Primary Key**: `id`
- **Relationships**: Courses (`learning_path_courses`), Organization.

### Media Assets (`media_assets`)
- **Primary Key**: `id`
- **Relationships**: Usage (`media_asset_usages`).

### Gradebook (`grading_schemes`, `grade_categories`, `grade_items`)
- **Primary Key**: `id`
- **Relationships**: Courses, Users.

### Audit & Logs (`audit_logs`, `activity_log`)
- **Primary Key**: `id`
- **Relationships**: User, Target Entity.

## Missing Constraints / Technical Debt
- Missing cascading deletes on standard child relations.
- Redundant soft-delete fields across intermediate tables.
- Legacy fields require cleanup.

## Database Ownership Map
- **Business Owner**: Platform Engineering
- **Parent Entity**: Organization (Tenant)
- **Child Entities**: Courses, Users, Reports
- **Creation/Update Workflows**: Builders create content, Learners consume, System updates progress.
