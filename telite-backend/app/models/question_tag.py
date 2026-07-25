from sqlalchemy import Column, ForeignKey, Integer, String

from app.models.base import Base


class QuestionTag(Base):
    __tablename__ = "question_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)

class QuestionTagMap(Base):
    __tablename__ = "question_tag_map"
    
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    question_version_id = Column(Integer, ForeignKey("question_versions.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    tag_id = Column(Integer, ForeignKey("question_tags.id", ondelete="CASCADE"), primary_key=True, nullable=False)
