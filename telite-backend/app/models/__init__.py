"""SQLAlchemy ORM models for Telite LMS."""

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.organization import Organization
from app.models.organization_branding import OrganizationBranding
from app.models.user import User
from app.models.membership import Membership
from app.models.category import Category
from app.models.course import Course
from app.models.enrollment import EnrollmentRequest
from app.models.task import Task
from app.models.task_workflow import TaskAssignment, TaskSubmission, TaskReview
from app.models.session import AuthSession
from app.models.notification import Notification
from app.models.announcement import Announcement, AnnouncementAudience, AnnouncementReadState
from app.models.gradebook import CompletionRule, CourseGrade, GradeCategory, GradeChangeAudit, GradeItem, GradeResult, GradingScheme
from app.models.audit import AuditLog, ActivityLog
from app.models.builder_activity_log import BuilderActivityLog
from app.models.course_edit_lock import CourseEditLock

from app.models.pal import PalQuizScore, PalRecommendation, PalTopicPerformance
from app.models.invitation import OrgInvitation
from app.models.pending_verification import PendingVerification
from app.models.password_reset_token import PasswordResetToken
from app.models.allowed_domain import AllowedDomain
from app.models.platform_setting import PlatformSetting
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.lesson_block_progress import LessonBlockProgress
from app.models.course_version import CourseVersion
from app.models.course_review import CourseReview
from app.models.learning_path import LearningPath, LearningPathCourse
from app.models.learning_path_progress import LearningPathProgress
from app.models.learner_event import LearnerEvent
from app.models.learner_activity_log import LearnerActivityLog
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.media_asset_usage import MediaAssetUsage

from app.models.question_bank import QuestionBank
from app.models.question import Question, QuestionVersion
from app.models.question_category import QuestionCategory
from app.models.question_tag import QuestionTag, QuestionTagMap
from app.models.question_import_job import QuestionImportJob
from app.models.quiz_attempt import QuizAttempt, QuizAttemptQuestion, QuizAttemptEvent
from app.models.quiz_answer import QuizAnswer, GradingEvent
from app.models.rubric import GradingRubric, RubricCriteria
from app.models.role_permission import RolePermission

from app.models.assignment_submission import AssignmentSubmission
from app.models.interactive_tracking import InteractiveTracking
from app.models.certificate import Certificate

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "Organization",
    "OrganizationBranding",
    "User",
    "Membership",
    "Category",
    "Course",
    "EnrollmentRequest",
    "Task",
    "TaskAssignment",
    "TaskSubmission",
    "TaskReview",
    "AuthSession",
    "Notification",
    "Announcement",
    "AnnouncementAudience",
    "AnnouncementReadState",
    "GradingScheme",
    "GradeCategory",
    "GradeItem",
    "GradeResult",
    "CourseGrade",
    "GradeChangeAudit",
    "CompletionRule",
    "AuditLog",
    "ActivityLog",
    "BuilderActivityLog",
    "CourseEditLock",
    "PalQuizScore",
    "PalRecommendation",
    "PalTopicPerformance",
    "OrgInvitation",
    "PendingVerification",
    "PasswordResetToken",
    "AllowedDomain",
    "PlatformSetting",
    "CourseModule",
    "CourseProgress",
    "ModuleProgress",
    "LessonBlockProgress",
    "CourseVersion",
    "CourseReview",
    "LearningPath",
    "LearningPathCourse",
    "LearningPathProgress",
    "LearnerEvent",
    "LearnerActivityLog",
    "CourseSection",
    "LessonBlock",
    "MediaAsset",
    "MediaAssetUsage",
    "QuestionBank",
    "Question",
    "QuestionVersion",
    "QuestionCategory",
    "QuestionTag",
    "QuestionTagMap",
    "QuestionImportJob",
    "QuizAttempt",
    "QuizAttemptQuestion",
    "QuizAttemptEvent",
    "QuizAnswer",
    "GradingEvent",
    "GradingRubric",
    "RubricCriteria",
    "RolePermission",
    "AssignmentSubmission",
    "InteractiveTracking",
    "Certificate",
]
