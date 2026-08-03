from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base


class QuestionImportJob(Base):
    __tablename__ = "question_import_jobs"
    
    id = Column(String(50), primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="UPLOADED") # UPLOADED, VALIDATED, READY_TO_COMMIT, COMMITTED, FAILED
    error_log = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
