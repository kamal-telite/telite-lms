"""Orchestrates CSV parsing, validation, and batch execution for bulk enrollments."""

import csv
import io
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import UserRepository
from app.services.enrollment_service import EnrollmentService, EnrollmentPermissionError, EnrollmentServiceError

@dataclass
class BulkPreviewRow:
    email: str
    full_name: str
    course_id: str
    is_valid: bool
    is_new_user: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "full_name": self.full_name,
            "course_id": self.course_id,
            "is_valid": self.is_valid,
            "is_new_user": self.is_new_user,
            "errors": self.errors,
        }

class BulkEnrollmentService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.course_repo = CourseRepository(db)
        self.enrollment_service = EnrollmentService(db)

    def parse_and_validate_csv(
        self,
        file_content: str,
        actor_token: TokenData
    ) -> list[BulkPreviewRow]:
        """Parses CSV content and validates each row without modifying the database."""
        
        # Security/RBAC check
        if not actor_token.is_platform_admin and actor_token.role not in self.enrollment_service.ALLOWED_ACTOR_ROLES:
            raise EnrollmentPermissionError("Admin access required")
        if not actor_token.org_id:
            raise EnrollmentPermissionError("Organization context is required")

        reader = csv.DictReader(io.StringIO(file_content))
        
        headers = reader.fieldnames or []
        if 'email' not in headers or 'course_id' not in headers:
            raise ValueError("CSV must contain 'email' and 'course_id' columns")

        # Pre-fetch existing courses in org to avoid N+1 validation queries
        # Since course catalogs are usually small (< 10,000), we can load their IDs.
        # However, it's safer to just load the requested course_ids.
        
        rows_data = list(reader)
        if len(rows_data) > 1000:
            raise ValueError("Maximum 1000 rows allowed per bulk upload in synchronous mode")

        unique_course_ids = {row.get('course_id', '').strip() for row in rows_data if row.get('course_id', '').strip()}
        
        # Load courses visible to actor's org
        valid_courses_query = self.course_repo.list_by_ids_for_org(list(unique_course_ids), actor_token.org_id)
        valid_course_map = {c.id: c for c in valid_courses_query if c.status in self.enrollment_service.LEARNER_VISIBLE_COURSE_STATUSES}

        # Check actor's category scope if they are a category admin
        actor_category_scope = actor_token.category_scope if (actor_token.role == "category_admin" and not actor_token.is_platform_admin) else None

        preview_rows = []
        for row in rows_data:
            email = row.get('email', '').strip()
            full_name = row.get('full_name', '').strip()
            course_id = row.get('course_id', '').strip()

            errors = []
            if not email:
                errors.append("Missing email")
            elif "@" not in email:
                errors.append("Invalid email format")

            if not course_id:
                errors.append("Missing course_id")

            # Validate Course
            course = valid_course_map.get(course_id)
            if course_id and not course:
                errors.append(f"Course {course_id} is invalid, not found, or not published")
            elif course and actor_category_scope and course.category_slug != actor_category_scope:
                errors.append(f"Permission denied: Course {course_id} is outside your category scope")

            # Validate User
            is_new_user = False
            if email and not any(err for err in errors if "email" in err.lower()):
                existing_user = self.user_repo.get_by_email(email)
                if not existing_user:
                    is_new_user = True
                elif existing_user.org_id != actor_token.org_id:
                    errors.append(f"User {email} belongs to a different organization")

            preview_rows.append(BulkPreviewRow(
                email=email,
                full_name=full_name,
                course_id=course_id,
                is_valid=len(errors) == 0,
                is_new_user=is_new_user,
                errors=errors
            ))

        return preview_rows

    def execute_batch(
        self,
        rows: list[dict[str, Any]],
        actor_token: TokenData
    ) -> dict[str, Any]:
        """
        Executes a batch of validated rows using best-effort batch processing.
        Each learner enrollment executes in its own isolated transaction.
        Failure for one learner never affects another learner.
        rows should be a list of dictionaries with 'email', 'full_name', and 'course_id'.
        Returns execution summary.
        """
        success_count = 0
        failure_count = 0
        errors = []

        if len(rows) > 1000:
            raise ValueError("Maximum 1000 rows allowed per batch")

        for idx, row in enumerate(rows):
            email = row.get('email', '').strip()
            full_name = row.get('full_name', '').strip()
            course_id = row.get('course_id', '').strip()

            # Each enrollment gets its own transaction for best-effort processing
            try:
                # Start a new transaction for this enrollment
                nested = self.db.begin_nested()
                
                try:
                    # We reuse the manual_enroll service which perfectly handles
                    # duplicate prevention, missing user provisioning, and RBAC.
                    self.enrollment_service.manual_enroll(
                        actor_token=actor_token,
                        full_name=full_name,
                        email=email,
                        course_ids=[course_id],
                        enrollment_type="bulk",
                        note="Enrolled via Bulk Upload"
                    )
                    # Commit this individual enrollment
                    nested.commit()
                    success_count += 1
                except Exception as e:
                    # Rollback only this enrollment, not the entire batch
                    nested.rollback()
                    raise
                    
            except EnrollmentPermissionError as e:
                failure_count += 1
                errors.append({"row": idx + 1, "email": email, "course_id": course_id, "error": str(e)})
            except EnrollmentServiceError as e:
                failure_count += 1
                errors.append({"row": idx + 1, "email": email, "course_id": course_id, "error": str(e)})
            except Exception as e:
                failure_count += 1
                errors.append({"row": idx + 1, "email": email, "course_id": course_id, "error": "Internal server error"})

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        }
