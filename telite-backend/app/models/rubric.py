from sqlalchemy import Column, Integer, String, ForeignKey, Float
from app.models.base import Base

class GradingRubric(Base):
    __tablename__ = "grading_rubrics"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

class RubricCriteria(Base):
    __tablename__ = "rubric_criteria"
    
    id = Column(Integer, primary_key=True, index=True)
    rubric_id = Column(Integer, ForeignKey("grading_rubrics.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    max_points = Column(Float, nullable=False)
