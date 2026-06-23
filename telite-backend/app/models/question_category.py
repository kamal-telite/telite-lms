from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base

class QuestionCategory(Base):
    __tablename__ = "question_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("question_categories.id", ondelete="CASCADE"), nullable=True, index=True)
