"""
PAL (Personalized Adaptive Learning) models.

PHASE 3: Migrated from separate SQLite database (pal_data.db) into
PostgreSQL with full org_id tenant isolation.

Previously these tables had NO org_id — PAL data was global across all
tenants. This migration fixes that critical isolation gap.
"""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class PalQuizScore(Base, TenantMixin, TimestampMixin):
    """Quiz scores for PAL engine — migrated from SQLite quiz_scores table."""

    __tablename__ = "pal_quiz_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    course_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quiz_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quiz_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synced_from_moodle: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "enrollment_number": self.enrollment_number,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "course_name": self.course_name,
            "topic": self.topic,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PalRecommendation(Base, TenantMixin, TimestampMixin):
    """PAL recommendations — migrated from SQLite recommendations table."""

    __tablename__ = "pal_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # remedial/normal/advanced
    weak_topics: Mapped[str | None] = mapped_column(Text, nullable=True)       # JSON array
    strong_topics: Mapped[str | None] = mapped_column(Text, nullable=True)     # JSON array
    recommended_courses: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON array
    recommended_resources: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON array
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    email_sent: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "enrollment_number": self.enrollment_number,
            "user_id": self.user_id,
            "level": self.level,
            "avg_score": self.avg_score,
            "email_sent": bool(self.email_sent),
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PalTopicPerformance(Base, TenantMixin, TimestampMixin):
    """Per-topic performance — migrated from SQLite topic_performance table."""

    __tablename__ = "pal_topic_performance"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_number", "topic", "org_id",
            name="uq_pal_topic_enrollment_org",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_updated: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "enrollment_number": self.enrollment_number,
            "user_id": self.user_id,
            "topic": self.topic,
            "avg_score": self.avg_score,
            "attempts": self.attempts,
            "org_id": self.org_id,
        }
