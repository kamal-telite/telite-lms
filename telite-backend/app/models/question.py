from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON
from app.models.base import Base

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("question_banks.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    current_version_id = Column(Integer, ForeignKey("question_versions.id", use_alter=True, name="fk_question_current_version"), nullable=True)

class QuestionVersion(Base):
    __tablename__ = "question_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    question_type = Column(String(50), nullable=False) # multiple_choice, true_false, essay
    question_text = Column(Text, nullable=False)
    options_json = Column(JSON, nullable=True)
    correct_answer_json = Column(JSON, nullable=True)
    points = Column(Integer, nullable=False, default=1)
    metadata_json = Column(JSON, nullable=True) # Future AI hooks
