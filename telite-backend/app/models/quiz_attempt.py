from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, JSON
from app.models.base import Base

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quiz_definitions.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="in_progress") # in_progress, submitted, needs_manual_grading, graded
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    total_score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Academic Integrity Metadata
    ip_address = Column(String(255), nullable=True)
    user_agent = Column(String(255), nullable=True)
    tab_switch_count = Column(Integer, nullable=False, default=0)

class QuizAttemptQuestion(Base):
    __tablename__ = "quiz_attempt_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_version_id = Column(Integer, ForeignKey("question_versions.id"), nullable=False)
    display_order = Column(Integer, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

class QuizAttemptEvent(Base):
    __tablename__ = "quiz_attempt_events"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False) # QUIZ_STARTED, ANSWER_SAVED, TAB_SWITCH, NETWORK_DISCONNECT, AUTO_SUBMIT, MANUAL_SUBMIT, GRADING_COMPLETED
    event_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metadata_json = Column(JSON, nullable=True)
