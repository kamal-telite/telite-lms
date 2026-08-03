from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        UniqueConstraint('attempt_id', 'question_version_id', name='uq_quiz_answers_attempt_question'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    question_version_id = Column(Integer, ForeignKey("question_versions.id"), nullable=False, index=True)
    response_json = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Float, nullable=True)
    instructor_feedback = Column(Text, nullable=True)

class GradingEvent(Base):
    __tablename__ = "grading_events"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    grader_id = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    previous_score = Column(Float, nullable=True)
    new_score = Column(Float, nullable=False)
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
