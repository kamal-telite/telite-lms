# TELITE LMS Entity Relationship Map

## Core Entity Flow
Org -> Categories -> Courses -> Sections -> Modules -> Blocks -> Assessments -> Certificates -> Learning Paths -> Analytics -> Notifications -> Media -> Users -> Roles -> Permissions

## Relationships

### One-to-One (1:1)
- User -> UserProfile (if applicable)
- Course -> CourseEditLock

### One-to-Many (1:N)
- Organization -> Categories
- Category -> Courses
- Course -> Sections
- Section -> Modules
- Module -> Blocks
- Course -> Reviews
- User -> EnrollmentRequests
- Organization -> Notifications

### Many-to-Many (M:N)
- LearningPaths -> Courses (`learning_path_courses`)
- Users -> Courses (Implicitly via Enrollments)
- Users -> LearningPaths (`learning_path_progress`)
- Users -> Roles -> Permissions
- Announcements -> Audiences (`announcement_audiences`)

## Visual Flow (Abstract)
The system roots ownership at the **Organization (Tenant)** level. Users belong to organizations via Memberships. Organizations own Categories, which logically group Courses. Courses break down into Sections, Modules, and Blocks (Lessons). Completions generate Analytics, Grades, and Certificates.
