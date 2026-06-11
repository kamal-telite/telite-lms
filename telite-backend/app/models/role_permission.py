"""RolePermission model for dynamic capability matrices."""

from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    permission_key: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "role": self.role,
            "permission_key": self.permission_key,
            "enabled": self.enabled,
        }
