from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, JSON, Text
from app.models.base import Base

class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_version_id = Column(Integer, ForeignKey("question_versions.id"), nullable=False)
    response_json = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Float, nullable=True)
    instructor_feedback = Column(Text, nullable=True)

class GradingEvent(Base):
    __tablename__ = "grading_events"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    grader_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    previous_score = Column(Float, nullable=True)
    new_score = Column(Float, nullable=False)
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
