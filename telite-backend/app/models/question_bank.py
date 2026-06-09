from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base

class QuestionBank(Base):
    __tablename__ = "question_banks"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    visibility = Column(String(50), nullable=False, default="tenant") # tenant, department, course, private
