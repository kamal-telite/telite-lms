from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base


class QuizSettings(Base):
    __tablename__ = "quiz_settings"
    __table_args__ = (
        UniqueConstraint('quiz_id', 'org_id', name='uq_quiz_settings_quiz_org'),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quiz_definitions.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    passing_score = Column(Integer, nullable=True)
    time_limit = Column(Integer, nullable=True)
    attempt_limit = Column(Integer, nullable=True)
    review_mode = Column(String(50), nullable=True)
    show_answers = Column(Boolean, nullable=True)
    show_score = Column(Boolean, nullable=True)
    settings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class QuizDefinition(Base):
    __tablename__ = "quiz_definitions"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("course_modules.id", name="quiz_definitions_module_id_fkey"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    passing_score = Column(Integer, nullable=True)
    time_limit = Column(Integer, nullable=True)
    attempt_limit = Column(Integer, nullable=True)
    review_mode = Column(String(50), nullable=True)
    settings_json = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)



