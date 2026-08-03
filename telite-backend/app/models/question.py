from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("question_banks.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("question_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    current_draft_version_id = Column(Integer, ForeignKey("question_versions.id", use_alter=True, name="fk_question_draft_version"), nullable=True, index=True)
    current_published_version_id = Column(Integer, ForeignKey("question_versions.id", use_alter=True, name="fk_question_pub_version"), nullable=True, index=True)

    @property
    def current_version_id(self):
        return self.current_draft_version_id or self.current_published_version_id

    @current_version_id.setter
    def current_version_id(self, value):
        self.current_draft_version_id = value

class QuestionVersion(Base):
    __tablename__ = "question_versions"
    __table_args__ = (
        UniqueConstraint('question_id', 'version_number', name='uq_question_versions_question_version'),
        CheckConstraint('version_number >= 1', name='chk_question_versions_version_number'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("question_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="DRAFT") # DRAFT, PUBLISHED, ARCHIVED
    question_type = Column(String(50), nullable=False) # multiple_choice, true_false, essay
    question_text = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=True)
    correct_answer_json = Column(JSON, nullable=True)
    points = Column(Integer, nullable=False, default=1)
    metadata_json = Column(JSON, nullable=True) # Future AI hooks
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
