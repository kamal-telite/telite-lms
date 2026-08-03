"""SQLAlchemy ORM models for Telite LMS."""

from app.models.allowed_domain import AllowedDomain
from app.models.announcement import Announcement, AnnouncementAudience, AnnouncementReadState
from app.models.assignment_submission import AssignmentSubmission
from app.models.audit import ActivityLog
from app.models.audit import AuditLog as AuditLogOld
from app.models.audit_log import AuditLog
from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.branding import BrandingAsset, BrandingAuditLog, BrandingVersion
from app.models.builder_activity_log import BuilderActivityLog
from app.models.category import Category
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.course_edit_lock import CourseEditLock
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.course_review import CourseReview
from app.models.course_section import CourseSection
from app.models.course_version import CourseVersion
from app.models.enrollment import EnrollmentRequest
from app.models.gradebook import (
    CompletionRule,
    CourseGrade,
    GradeCategory,
    GradeChangeAudit,
    GradeItem,
    GradeResult,
    GradingScheme,
)
from app.models.interactive_tracking import InteractiveTracking
from app.models.invitation import OrgInvitation
from app.models.learner_activity_log import LearnerActivityLog
from app.models.learner_event import LearnerEvent
from app.models.learning_path import LearningPath, LearningPathCourse
from app.models.learning_path_progress import LearningPathProgress
from app.models.learning_session import LearningSession
from app.models.lesson_block import LessonBlock
from app.models.lesson_block_progress import LessonBlockProgress
from app.models.media_asset import MediaAsset
from app.models.media_asset_usage import MediaAssetUsage
from app.models.membership import Membership
from app.models.module_progress import ModuleProgress
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference, OrganizationNotificationDefault, NotificationCategory
from app.models.organization import Organization
from app.models.organization_branding import OrganizationBranding
from app.models.pal import PalQuizScore, PalRecommendation, PalTopicPerformance
from app.models.password_reset_token import PasswordResetToken
from app.models.pending_verification import PendingVerification
from app.models.platform_setting import PlatformSetting
from app.models.progression_rule import ProgressionRule
from app.models.question import Question, QuestionVersion
from app.models.question_bank import QuestionBank
from app.models.question_category import QuestionCategory
from app.models.question_import_job import QuestionImportJob
from app.models.question_tag import QuestionTag, QuestionTagMap
from app.models.quiz_answer import GradingEvent, QuizAnswer
from app.models.quiz_attempt import QuizAttempt, QuizAttemptEvent, QuizAttemptQuestion
from app.models.quiz_models import QuizDefinition, QuizSettings
from app.models.role_permission import RolePermission
from app.models.rubric import GradingRubric, RubricCriteria
from app.models.session import AuthSession
from app.models.task import Task
from app.models.task_workflow import TaskAssignment, TaskReview, TaskSubmission
from app.models.user import User

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "Organization",
    "OrganizationBranding",
    "BrandingVersion",
    "BrandingAsset",
    "BrandingAuditLog",
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
    "NotificationPreference",
    "OrganizationNotificationDefault",
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
    "QuizDefinition",

    "QuizSettings",
    "QuizAttempt",
    "QuizAttemptQuestion",
    "QuizAttemptEvent",
    "QuizAnswer",
    "GradingEvent",
    "GradingRubric",
    "RubricCriteria",
    "RolePermission",
    "AssignmentSubmission",
    "LearningSession",
    "InteractiveTracking",
    "Certificate",
    "ProgressionRule",
]
