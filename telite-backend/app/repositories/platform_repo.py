from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.allowed_domain import AllowedDomain
from app.models.platform_setting import PlatformSetting
from app.repositories.base_repo import BaseRepository

class PlatformRepository(BaseRepository[PlatformSetting]):
    model = PlatformSetting

    def get_setting(self, key: str) -> Any | None:
        stmt = select(PlatformSetting).where(PlatformSetting.setting_key == key)
        record = self.session.execute(stmt).scalar_one_or_none()
        if not record:
            return None
        return json.loads(record.setting_value_json)

    def set_setting(self, key: str, value: Any, updated_by: str | None = None) -> PlatformSetting:
        stmt = select(PlatformSetting).where(PlatformSetting.setting_key == key)
        record = self.session.execute(stmt).scalar_one_or_none()
        
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        val_json = json.dumps(value)
        if record:
            record.setting_value_json = val_json
            record.updated_by = updated_by
            record.updated_at = now
        else:
            record = PlatformSetting(
                setting_key=key,
                setting_value_json=val_json,
                updated_by=updated_by,
                updated_at=now,
            )
            self.session.add(record)
        self.session.flush()
        return record

    def list_allowed_domains(self) -> Sequence[AllowedDomain]:
        stmt = select(AllowedDomain).order_by(AllowedDomain.domain)
        return self.session.execute(stmt).scalars().all()

    def add_allowed_domain(self, domain: str, label: str, added_by: str | None = None, org_id: int | None = None) -> AllowedDomain:
        stmt = select(AllowedDomain).where(AllowedDomain.domain == domain.lower().strip())
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing:
            raise ValueError(f"Domain {domain} is already allowed.")
        
        record = AllowedDomain(
            domain=domain.lower().strip(),
            label=label,
            added_by=added_by,
            org_id=org_id,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def remove_allowed_domain(self, domain: str) -> None:
        stmt = select(AllowedDomain).where(AllowedDomain.domain == domain.lower().strip())
        record = self.session.execute(stmt).scalar_one_or_none()
        if record:
            self.session.delete(record)
            self.session.flush()
