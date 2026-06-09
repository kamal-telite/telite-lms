from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean

from app.models.base import Base

class QuizDefinition(Base):
    __tablename__ = "quiz_definitions"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    passing_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True)

class QuizSettings(Base):
    __tablename__ = "quiz_settings"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quiz_definitions.id"), nullable=False, index=True)
    time_limit = Column(Integer, nullable=True)
    passing_score = Column(Float, nullable=True)
    attempt_limit = Column(Integer, nullable=True)
    show_answers = Column(Boolean, nullable=False, default=False)
    show_score = Column(Boolean, nullable=False, default=True)
    shuffle_questions = Column(Boolean, nullable=False, default=False)
    shuffle_options = Column(Boolean, nullable=False, default=False)
    cooldown_minutes = Column(Integer, nullable=True)
    review_mode = Column(String(50), nullable=False, default="score_only") # none, score_only, answers_after_submit, answers_after_due_date, full_review
