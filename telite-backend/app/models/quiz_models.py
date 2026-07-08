from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base


class QuizSettings(Base):
    __tablename__ = "quiz_settings"

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
    module_id = Column(Integer, nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    passing_score = Column(Integer, nullable=True)
    time_limit = Column(Integer, nullable=True)
    attempt_limit = Column(Integer, nullable=True)
    review_mode = Column(String(50), nullable=True)
    settings_json = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    quiz_questions = relationship("QuizDefinitionQuestion", back_populates="quiz")


class QuizDefinitionQuestion(Base):
    __tablename__ = "quiz_definition_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quiz_definitions.id"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    question_version_id = Column(Integer, nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    quiz = relationship("QuizDefinition", back_populates="quiz_questions")
