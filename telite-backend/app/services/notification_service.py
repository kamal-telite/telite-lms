import logging
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.notification_repo import NotificationRepository
from app.models.user import User
from app.services.preference_resolver import PreferenceResolver
from app.services.notification_category_mapper import event_to_category

logger = logging.getLogger("telite.notifications")

class NotificationService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = NotificationRepository(session)
        self.resolver = PreferenceResolver(session)

    def emit_event(
        self,
        event_name: str,
        org_id: int,
        context: dict[str, Any],
        recipient_id: str | None = None,
    ):
        """
        Emits a single-user synchronous notification domain event.
        The NotificationService is responsible for transforming this domain event
        into a notification payload, checking preferences, and persisting it.
        """
        if not recipient_id:
            logger.warning(f"NotificationService.emit_event called without recipient_id for event {event_name}")
            return

        payload = self._build_payload(event_name, context)
        if not payload:
            return
            
        category_str = event_to_category(event_name)
        prefs = self.resolver.resolve_for_user(recipient_id, org_id, category_str)
        
        if not prefs["in_app"] and not prefs["email"]:
            logger.info("Notification skipped for user %s due to preferences (in_app=False, email=False)", recipient_id)
            return

        metadata = payload.get("metadata", {})
        if prefs["email"]:
            metadata["delivery_channel"] = "email"
        if not prefs["in_app"]:
            metadata["hidden_in_app"] = True
            
        self.repo.create_once(
            user_id=recipient_id,
            org_id=org_id,
            title=payload["title"],
            message=payload["message"],
            notif_type=payload["type"],
            idempotency_key=payload["idempotency_key"],
            metadata=metadata,
            source_type=payload["source_type"],
            source_id=payload["source_id"]
        )

    def fanout_event(
        self,
        event_name: str,
        org_id: int,
        context: dict[str, Any],
        audience: dict[str, Any]
    ):
        """
        Dispatches a fanout notification domain event asynchronously.
        """
        from app.workers.notification_tasks import dispatch_fanout_task
        dispatch_fanout_task.delay(event_name, org_id, context, audience)

    def _build_payload(self, event_name: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Centralized payload mapping based on domain event names.
        """
        if event_name == "enrollment.manual":
            course_id = context.get("course_id")
            course_title = context.get("course_title", "a course")
            timestamp = context.get("timestamp", "")
            return {
                "title": "You've been enrolled!",
                "message": f"You were manually enrolled in {course_title}.",
                "type": "enrollment",
                "idempotency_key": f"enrollment_manual_{course_id}_{timestamp}",
                "source_type": "course",
                "source_id": str(course_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_id}"
                }
            }
        
        if event_name == "enrollment.approved":
            course_title = context.get("category_slug", "a course")
            request_id = context.get("request_id", "")
            return {
                "title": "Enrollment Approved",
                "message": f"Your request to enroll in {course_title} was approved.",
                "type": "enrollment",
                "idempotency_key": f"enrollment_approved_{request_id}",
                "source_type": "enrollment_request",
                "source_id": request_id,
                "metadata": {
                    "action_url": f"/learner/dashboard"
                }
            }

        if event_name == "enrollment.rejected":
            course_title = context.get("category_slug", "a course")
            request_id = context.get("request_id", "")
            reason = context.get("reason", "No reason provided.")
            return {
                "title": "Enrollment Rejected",
                "message": f"Your request to enroll in {course_title} was rejected. Reason: {reason}",
                "type": "enrollment",
                "idempotency_key": f"enrollment_rejected_{request_id}",
                "source_type": "enrollment_request",
                "source_id": request_id,
                "metadata": {}
            }
        
        if event_name == "course.created":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "a course")
            creator_name = context.get("creator_name", "Someone")
            return {
                "title": "New Course Created",
                "message": f"'{course_name}' was created by {creator_name}.",
                "type": "course_created",
                "idempotency_key": f"course_created:{course_id}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {
                    "action_url": f"/authoring/courses/{course_id}"
                }
            }

        if event_name == "course.published":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "your course")
            version = context.get("version", "")
            return {
                "title": "Course Published",
                "message": f"Your course '{course_name}' has been published.",
                "type": "course_published",
                "idempotency_key": f"course_published_{course_id}_{version}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {
                    "action_url": f"/authoring/courses/{course_id}"
                }
            }

        if event_name == "course.rejected":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "your course")
            return {
                "title": "Course Requires Changes",
                "message": f"Your course '{course_name}' was returned for revision.",
                "type": "course_rejected",
                "idempotency_key": f"course_rejected_{course_id}_{context.get('timestamp', '')}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {
                    "action_url": f"/authoring/courses/{course_id}"
                }
            }

        if event_name == "course.updated":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "a course")
            return {
                "title": "Course Updated",
                "message": f"'{course_name}' has been updated.",
                "type": "course_updated",
                "idempotency_key": f"course_updated:{course_id}:{context.get('timestamp', '')}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {
                    "action_url": f"/learner/courses/{course_id}"
                }
            }

        if event_name == "course.archived":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "a course")
            return {
                "title": "Course Archived",
                "message": f"'{course_name}' has been archived and is no longer available.",
                "type": "course_archived",
                "idempotency_key": f"course_archived:{course_id}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {}
            }

        if event_name == "course.deleted":
            course_id = context.get("course_id", "")
            course_name = context.get("course_name", "a course")
            return {
                "title": "Course Deleted",
                "message": f"'{course_name}' has been permanently deleted.",
                "type": "course_deleted",
                "idempotency_key": f"course_deleted:{course_id}",
                "source_type": "course",
                "source_id": course_id,
                "metadata": {}
            }

        if event_name == "assignment.submitted":
            course_slug = context.get("course_slug", "")
            block_id = context.get("block_id", "")
            submission_id = context.get("submission_id", "")
            
            return {
                "title": "Assignment Submitted",
                "message": "Your assignment has been submitted and is pending review.",
                "type": "assignment_submitted",
                "idempotency_key": f"assignment_submitted:{submission_id}",
                "source_type": "assignment_submission",
                "source_id": str(submission_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_slug}/learn/{block_id}"
                }
            }

        if event_name == "assignment.graded":
            submission_id = context.get("submission_id", "")
            return {
                "title": "Assignment Graded",
                "message": "Your assignment has been graded.",
                "type": "assignment_graded",
                "idempotency_key": f"assignment_graded:{submission_id}",
                "source_type": "assignment",
                "source_id": str(submission_id),
                "metadata": context.get("metadata", {})
            }

        if event_name == "assignment.approved":
            submission_id = context.get("submission_id", "")
            return {
                "title": "Assignment Approved",
                "message": "Your assignment has been approved.",
                "type": "info",
                "idempotency_key": f"assignment_approved:{submission_id}",
                "source_type": "assignment",
                "source_id": str(submission_id),
                "metadata": {}
            }

        if event_name == "assignment.rejected":
            submission_id = context.get("submission_id", "")
            feedback = context.get("feedback") or "Your assignment was rejected. Please review the feedback."
            return {
                "title": "Assignment Rejected",
                "message": feedback,
                "type": "info",
                "idempotency_key": f"assignment_rejected:{submission_id}",
                "source_type": "assignment",
                "source_id": str(submission_id),
                "metadata": {}
            }

        if event_name == "quiz.submitted":
            course_slug = context.get("course_slug", "")
            quiz_id = context.get("quiz_id", "")
            quiz_title = context.get("quiz_title", "a quiz")
            attempt_id = context.get("attempt_id", "")
            
            return {
                "title": "Quiz Submitted",
                "message": f"Your submission for '{quiz_title}' has been received.",
                "type": "info",
                "idempotency_key": f"quiz_submitted:{attempt_id}",
                "source_type": "quiz_attempt",
                "source_id": str(attempt_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_slug}/learn/{quiz_id}"
                }
            }

        if event_name == "quiz.graded":
            quiz_title = context.get("quiz_title", "a quiz")
            attempt_id = context.get("attempt_id", "")
            
            return {
                "title": "Quiz Graded",
                "message": f"Your attempt for '{quiz_title}' has been graded.",
                "type": "info",
                "idempotency_key": f"quiz_graded:{attempt_id}",
                "source_type": "quiz_attempt",
                "source_id": str(attempt_id),
                "metadata": {}
            }

        if event_name == "module.completed":
            course_slug = context.get("course_slug", "")
            module_id = context.get("module_id", "")
            module_title = context.get("module_title", "a module")
            
            return {
                "title": "Module Completed",
                "message": f"You have completed '{module_title}'.",
                "type": "info",
                "idempotency_key": f"module_completed:{module_id}",
                "source_type": "module",
                "source_id": str(module_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_slug}"
                }
            }

        if event_name == "course.completed":
            course_slug = context.get("course_slug", "")
            course_id = context.get("course_id", "")
            course_title = context.get("course_title", "a course")
            
            return {
                "title": "Course Completed",
                "message": f"Congratulations! You have completed '{course_title}'.",
                "type": "info",
                "idempotency_key": f"course_completed:{course_id}",
                "source_type": "course",
                "source_id": str(course_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_slug}"
                }
            }

        if event_name == "certificate.generated":
            course_slug = context.get("course_slug", "")
            course_id = context.get("course_id", "")
            course_title = context.get("course_title", "a course")
            certificate_id = context.get("certificate_id", "")
            
            return {
                "title": "Certificate Awarded",
                "message": f"You have earned a certificate for '{course_title}'.",
                "type": "info",
                "idempotency_key": f"certificate_generated:{certificate_id}",
                "source_type": "certificate",
                "source_id": str(certificate_id),
                "metadata": {
                    "action_url": f"/learner/courses/{course_slug}/certificate/{certificate_id}"
                }
            }

        if event_name == "user.joined":
            invited_email = context.get("invited_email", "")
            role = context.get("role", "")
            user_id = context.get("user_id", "")
            
            return {
                "title": "User Joined",
                "message": f"User {invited_email} has accepted their invitation and joined as {role}.",
                "type": "info",
                "idempotency_key": f"user_joined:{user_id}",
                "source_type": "user",
                "source_id": str(user_id),
                "metadata": {}
            }

        if event_name == "user.role_changed":
            new_role = context.get("new_role", "")
            user_id = context.get("user_id", "")
            
            return {
                "title": "Role Changed",
                "message": f"Your role has been updated to {new_role}.",
                "type": "info",
                "idempotency_key": f"role_changed:{user_id}:{context.get('timestamp', '')}",
                "source_type": "user",
                "source_id": str(user_id),
                "metadata": {}
            }

        if event_name == "announcement.published":
            announcement_id = context.get("announcement_id", "")
            title = context.get("title", "New Announcement")
            body = context.get("body", "")
            
            return {
                "title": f"New Announcement: {title}",
                "message": body[:200] + "..." if len(body) > 200 else body,
                "type": "announcement",
                "idempotency_key": f"announcement_published:{announcement_id}",
                "source_type": "announcement",
                "source_id": str(announcement_id),
                "metadata": {
                    "announcement_id": str(announcement_id)
                }
            }

        if event_name == "learning_path.assigned":
            path_id = context.get("path_id", "")
            return {
                "title": "Learning Path Assigned",
                "message": "A new learning path has been assigned to you.",
                "type": "learning_path_assigned",
                "idempotency_key": f"learning_path_assigned:{path_id}",
                "source_type": "learning_path",
                "source_id": str(path_id),
                "metadata": {
                    "path_id": str(path_id)
                }
            }

        if event_name == "learning_path.completed":
            path_id = context.get("path_id", "")
            return {
                "title": "Learning Path Completed",
                "message": "You completed a learning path.",
                "type": "learning_path_completed",
                "idempotency_key": f"learning_path_completed:{path_id}",
                "source_type": "learning_path",
                "source_id": str(path_id),
                "metadata": {
                    "path_id": str(path_id)
                }
            }
            
        if event_name == "learning_path.course_unlocked":
            path_id = context.get("path_id", "")
            course_id = context.get("course_id", "")
            return {
                "title": "Course Unlocked",
                "message": "A new course is available in your learning path.",
                "type": "learning_path_unlocked",
                "idempotency_key": f"learning_path_unlocked:{path_id}:{course_id}",
                "source_type": "learning_path",
                "source_id": str(path_id),
                "metadata": {
                    "path_id": str(path_id),
                    "course_id": str(course_id)
                }
            }

        if event_name == "task.assigned":
            task_id = context.get("task_id", "")
            title = context.get("title", "")
            assignment_id = context.get("assignment_id", "")
            return {
                "title": "New task assigned",
                "message": f"New task assigned: {title}",
                "type": "task_assigned",
                "idempotency_key": f"task_assigned:{assignment_id}",
                "source_type": "task",
                "source_id": str(task_id),
                "metadata": {
                    "task_id": str(task_id),
                    "assignment_id": str(assignment_id)
                }
            }

        if event_name in ("task.approved", "task.revision_requested", "task.rejected"):
            task_id = context.get("task_id", "")
            title = context.get("title", "")
            assignment_id = context.get("assignment_id", "")
            
            review_status = event_name.split(".")[1]
            if review_status == "approved":
                n_title = "Task approved"
                n_body = "Your task has been approved."
            elif review_status == "revision_requested":
                n_title = "Revision requested"
                n_body = f"Revision requested on your task: {title}"
            else:
                n_title = "Task rejected"
                n_body = f"Your task was rejected: {title}"
                
            return {
                "title": n_title,
                "message": n_body,
                "type": f"task_{review_status}",
                "idempotency_key": f"task_{review_status}:{assignment_id}",
                "source_type": "task",
                "source_id": str(task_id),
                "metadata": {
                    "task_id": str(task_id),
                    "assignment_id": str(assignment_id)
                }
            }

        logger.warning(f"Unhandled event_name '{event_name}' in NotificationService")
        return None
