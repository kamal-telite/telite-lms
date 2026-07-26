"""Analytics repository - modularized for maintainability.

This module consolidates all analytics queries into a single repository class
while maintaining separation of concerns across multiple sub-modules:

- utils: Shared utility functions (rounding, JSON parsing, formatting)
- platform_analytics: Platform-level overview queries
- category_analytics: Category-specific metrics and dashboards
- global_analytics: Super-admin global KPIs and rankings
- learner_analytics: Learner-specific dashboard metrics
- engagement_analytics: Progress distribution and engagement heatmaps
- grading_analytics: Gradebook and grading statistics
"""

from typing import Any
from sqlalchemy.orm import Session

from app.models.learner_event import LearnerEvent
from app.repositories.base_repo import BaseRepository
from app.repositories.analytics.utils import (
    round_value,
    safe_json_list,
    iso_format,
    event_status,
    event_type as analytics_event_type,
    event_title,
)
from app.repositories.analytics.platform_analytics import get_platform_overview
from app.repositories.analytics.category_analytics import get_category_metrics
from app.repositories.analytics.global_analytics import get_global_kpis, get_cohort_rankings
from app.repositories.analytics.learner_analytics import get_learner_summary
from app.repositories.analytics.engagement_analytics import (
    get_progress_distribution,
    get_engagement_heatmap,
)
from app.repositories.analytics.grading_analytics import (
    get_grading_analytics_category_admin,
    get_grading_analytics_learner,
    get_grading_analytics_super_admin,
)


class AnalyticsRepository(BaseRepository[LearnerEvent]):
    """Analytics repository for dashboard and reporting views.
    
    Replaces the legacy raw SQL reporting from legacy_sql_repo.py.
    Aggregates data using SQLAlchemy and the learner_events ledger.
    """
    model = LearnerEvent

    # Utility methods (exposed for backward compatibility)
    @staticmethod
    def _round(value: float | int | None, digits: int = 1) -> float:
        return round_value(value, digits)

    @staticmethod
    def _safe_json_list(raw: str | None) -> list[dict[str, Any]]:
        return safe_json_list(raw)

    @staticmethod
    def _iso(value: Any) -> str | None:
        return iso_format(value)

    @staticmethod
    def _event_status(event_type: str) -> str:
        return event_status(event_type)

    @staticmethod
    def _event_type(raw_event_type: str) -> str:
        return analytics_event_type(raw_event_type)

    @staticmethod
    def _event_title(event: LearnerEvent, learner_name: str, course_name: str | None, module_title: str | None) -> str:
        return event_title(event.event_type, learner_name, course_name, module_title)

    # Platform-level analytics
    def get_platform_overview(self) -> dict[str, Any]:
        """Return the strict platform overview contract consumed by admin UI."""
        return get_platform_overview(self.session)

    # Global/Super Admin analytics
    def get_global_kpis(self, org_id: int | None = None) -> dict[str, Any]:
        """Provides KPIs for Super Admin Dashboard."""
        return get_global_kpis(self.session, org_id)

    def get_cohort_rankings(
        self,
        category_slug: str | None = None,
        org_id: int | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Returns PAL leaderboard rankings based on dynamic PAL scores."""
        return get_cohort_rankings(self.session, category_slug, org_id, limit)

    # Category-level analytics
    def get_category_metrics(
        self,
        category_slug: str,
        org_id: int | None = None
    ) -> dict[str, Any]:
        """Provides metrics for Category Admin Dashboard."""
        return get_category_metrics(self.session, category_slug, org_id)

    def get_stats_breakdown(
        self,
        category_slug: str,
        org_id: int | None = None
    ) -> dict[str, Any]:
        """Provides metrics for deep-dive Stats Dashboard."""
        metrics = self.get_category_metrics(category_slug, org_id)
        return {
            "category": metrics["category"],
            "kpis": {
                "active_courses": metrics["kpis"]["total_courses"],
                "enrolled_learners": metrics["kpis"]["active_learners"],
                "avg_completion": metrics["kpis"]["avg_completion"],
            },
            "course_completion": get_progress_distribution(category_slug, org_id),
            "heatmap": get_engagement_heatmap(category_slug, org_id),
            "leaderboard": self.get_cohort_rankings(category_slug, org_id, limit=5),
            "full_leaderboard": self.get_cohort_rankings(category_slug, org_id),
        }

    # Learner analytics
    def get_learner_summary(self, user_id: str) -> dict[str, Any]:
        """Provides metrics for Learner Dashboard."""
        return get_learner_summary(self.session, user_id)

    # Engagement analytics
    def get_progress_distribution(
        self,
        category_slug: str | None = None,
        org_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Calculates completion distribution from COURSE_COMPLETED events."""
        return get_progress_distribution(self.session, category_slug, org_id)

    def get_engagement_heatmap(
        self,
        category_slug: str | None = None,
        org_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Calculates engagement weight based on HEARTBEAT, BLOCK_VIEWED, and interactive blocks."""
        return get_engagement_heatmap(self.session, category_slug, org_id)

    # Grading analytics
    def get_grading_analytics_super_admin(self, org_id: int | None = None) -> dict[str, Any]:
        """Returns organization-wide grading analytics for Super Admin dashboard."""
        return get_grading_analytics_super_admin(self.session, org_id)

    def get_grading_analytics_category_admin(
        self,
        category_slug: str,
        org_id: int | None = None,
    ) -> dict[str, Any]:
        """Returns live category grading analytics for Category Admin dashboard."""
        return get_grading_analytics_category_admin(self.session, category_slug, org_id)

    def get_grading_analytics_learner(self, user_id: str) -> dict[str, Any]:
        """Returns learner-specific grading analytics for Learner dashboard."""
        return get_grading_analytics_learner(self.session, user_id)


# Export the main repository class
__all__ = ["AnalyticsRepository"]
