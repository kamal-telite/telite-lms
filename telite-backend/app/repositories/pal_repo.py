"""
PALRepository — Personalized Adaptive Learning data access.

PHASE 3: Replaces the separate SQLite pal_db.py with PostgreSQL-backed
repositories that include full org_id tenant isolation.

Previously PAL data was GLOBAL (no org_id) — this fixes that critical gap.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.pal import PalQuizScore, PalRecommendation, PalTopicPerformance
from app.repositories.base_repo import BaseRepository


class PalRepository:
    """
    Unified PAL repository combining quiz scores, recommendations,
    and topic performance — all org-scoped.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.scores = PalScoreRepository(session)
        self.recommendations = PalRecommendationRepository(session)
        self.topics = PalTopicRepository(session)

    def get_student_summary(
        self, enrollment_number: str, org_id: int
    ) -> dict[str, Any]:
        """Full PAL summary for a student — used by the PAL engine."""
        scores = self.scores.get_for_student(enrollment_number, org_id)
        topics = self.topics.get_for_student(enrollment_number, org_id)
        latest_rec = self.recommendations.get_latest(enrollment_number, org_id)

        avg_score = (
            sum(s.score for s in scores) / len(scores) if scores else 0.0
        )

        return {
            "enrollment_number": enrollment_number,
            "org_id": org_id,
            "avg_score": round(avg_score, 2),
            "total_quizzes": len(scores),
            "scores": [s.to_dict() for s in scores],
            "topics": [t.to_dict() for t in topics],
            "recommendation": latest_rec.to_dict() if latest_rec else None,
        }

    def get_all_students_summary(self, org_id: int) -> list[dict[str, Any]]:
        """Admin view — summary for all students in an org."""
        stmt = (
            select(
                PalQuizScore.enrollment_number,
                func.avg(PalQuizScore.score).label("avg_score"),
                func.count(PalQuizScore.id).label("total_quizzes"),
            )
            .where(PalQuizScore.org_id == org_id)
            .group_by(PalQuizScore.enrollment_number)
            .order_by(func.avg(PalQuizScore.score).desc())
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "enrollment_number": r.enrollment_number,
                "avg_score": round(float(r.avg_score or 0), 2),
                "total_quizzes": r.total_quizzes,
            }
            for r in rows
        ]


class PalScoreRepository(BaseRepository[PalQuizScore]):
    model = PalQuizScore

    def get_for_student(
        self, enrollment_number: str, org_id: int
    ) -> Sequence[PalQuizScore]:
        stmt = (
            select(PalQuizScore)
            .where(PalQuizScore.enrollment_number == enrollment_number)
            .where(PalQuizScore.org_id == org_id)
            .order_by(PalQuizScore.created_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def insert_score(
        self,
        *,
        enrollment_number: str,
        org_id: int,
        course_id: int,
        score: float,
        max_score: float = 100.0,
        topic: str | None = None,
        course_name: str | None = None,
        quiz_id: int | None = None,
        quiz_name: str | None = None,
        user_id: str | None = None,
        synced_from_moodle: bool = False,
    ) -> PalQuizScore:
        percentage = round((score / max_score) * 100, 2) if max_score > 0 else 0.0
        record = PalQuizScore(
            enrollment_number=enrollment_number,
            org_id=org_id,
            user_id=user_id,
            course_id=course_id,
            course_name=course_name,
            quiz_id=quiz_id,
            quiz_name=quiz_name,
            topic=topic,
            score=score,
            max_score=max_score,
            percentage=percentage,
            synced_from_moodle=synced_from_moodle,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_avg_score(self, enrollment_number: str, org_id: int) -> float:
        stmt = (
            select(func.avg(PalQuizScore.score))
            .where(PalQuizScore.enrollment_number == enrollment_number)
            .where(PalQuizScore.org_id == org_id)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return round(float(result or 0.0), 2)


class PalRecommendationRepository(BaseRepository[PalRecommendation]):
    model = PalRecommendation

    def get_latest(
        self, enrollment_number: str, org_id: int
    ) -> PalRecommendation | None:
        stmt = (
            select(PalRecommendation)
            .where(PalRecommendation.enrollment_number == enrollment_number)
            .where(PalRecommendation.org_id == org_id)
            .order_by(PalRecommendation.created_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def save_recommendation(
        self,
        *,
        enrollment_number: str,
        org_id: int,
        level: str,
        avg_score: float,
        weak_topics: list[str],
        strong_topics: list[str],
        recommended_courses: list[str],
        recommended_resources: list[str],
        user_id: str | None = None,
    ) -> PalRecommendation:
        rec = PalRecommendation(
            enrollment_number=enrollment_number,
            org_id=org_id,
            user_id=user_id,
            level=level,
            avg_score=avg_score,
            weak_topics=json.dumps(weak_topics),
            strong_topics=json.dumps(strong_topics),
            recommended_courses=json.dumps(recommended_courses),
            recommended_resources=json.dumps(recommended_resources),
            email_sent=False,
        )
        self.session.add(rec)
        self.session.flush()
        return rec

    def mark_email_sent(self, rec_id: int) -> None:
        self.session.execute(
            update(PalRecommendation)
            .where(PalRecommendation.id == rec_id)
            .values(email_sent=True)
        )


class PalTopicRepository(BaseRepository[PalTopicPerformance]):
    model = PalTopicPerformance

    def get_for_student(
        self, enrollment_number: str, org_id: int
    ) -> Sequence[PalTopicPerformance]:
        stmt = (
            select(PalTopicPerformance)
            .where(PalTopicPerformance.enrollment_number == enrollment_number)
            .where(PalTopicPerformance.org_id == org_id)
            .order_by(PalTopicPerformance.avg_score.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_weak_topics(
        self, enrollment_number: str, org_id: int, threshold: float = 60.0
    ) -> Sequence[PalTopicPerformance]:
        stmt = (
            select(PalTopicPerformance)
            .where(PalTopicPerformance.enrollment_number == enrollment_number)
            .where(PalTopicPerformance.org_id == org_id)
            .where(PalTopicPerformance.avg_score < threshold)
            .order_by(PalTopicPerformance.avg_score.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def upsert_topic(
        self,
        *,
        enrollment_number: str,
        org_id: int,
        topic: str,
        score: float,
        user_id: str | None = None,
    ) -> PalTopicPerformance:
        """Update running average for a topic, or create if not exists."""
        from datetime import datetime
        existing = self.session.execute(
            select(PalTopicPerformance).where(
                PalTopicPerformance.enrollment_number == enrollment_number,
                PalTopicPerformance.topic == topic,
                PalTopicPerformance.org_id == org_id,
            )
        ).scalar_one_or_none()

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if existing is None:
            record = PalTopicPerformance(
                enrollment_number=enrollment_number,
                org_id=org_id,
                user_id=user_id,
                topic=topic,
                avg_score=score,
                attempts=1,
                last_updated=now,
            )
            self.session.add(record)
        else:
            # Incremental running average
            new_avg = (
                (existing.avg_score * existing.attempts + score)
                / (existing.attempts + 1)
            )
            existing.avg_score = round(new_avg, 2)
            existing.attempts += 1
            existing.last_updated = now
            record = existing

        self.session.flush()
        return record
