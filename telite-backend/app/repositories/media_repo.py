"""
Media Repository for Course Assets.
Handles creation, retrieval, and soft deletion of media assets.
"""

from __future__ import annotations
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.media_asset import MediaAsset
from app.repositories.base_repo import BaseRepository
from app.models.builder_activity_log import BuilderActivityLog

class MediaRepository(BaseRepository):

    def get_assets(self, org_id: int) -> Sequence[MediaAsset]:
        stmt = (
            select(MediaAsset)
            .where(MediaAsset.org_id == org_id, MediaAsset.deleted_at.is_(None))
            .order_by(MediaAsset.created_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_asset_by_id(self, asset_id: int, org_id: int) -> MediaAsset | None:
        stmt = select(MediaAsset).where(
            MediaAsset.id == asset_id, 
            MediaAsset.org_id == org_id,
            MediaAsset.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def save_asset(self, asset: MediaAsset) -> MediaAsset:
        self.session.add(asset)
        self.session.flush()
        return asset

    def delete_asset(self, asset: MediaAsset, deleted_by: str) -> None:
        asset.deleted_at = datetime.now(timezone.utc)
        asset.deleted_by = deleted_by
        self.session.flush()

    def log_activity(self, user_id: str, org_id: int, action: str, payload: str = "{}") -> BuilderActivityLog:
        # We can use course_id="" or "library" for media-only actions if they aren't bound to a specific course
        log = BuilderActivityLog(
            course_id="MEDIA_LIBRARY",
            user_id=user_id,
            org_id=org_id,
            action=action,
            payload=payload
        )
        self.session.add(log)
        self.session.flush()
        return log
