"""
SnapshotResolver — resolves learner-facing content from CourseVersion snapshots.

When a learner is pinned to a published version (enrolled_version), all content
must be served from the frozen snapshot_json, not from live Draft tables.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.course_progress import CourseProgress
from app.models.course_version import CourseVersion
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset


class SnapshotResolver:
    def __init__(self, db: Session):
        self.db = db

    def _get_enrolled_version(self, user_id: str, course_id: str) -> Optional[int]:
        """Return the enrolled version number for this learner, or None."""
        progress = self.db.execute(
            select(CourseProgress).where(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id
            )
        ).scalars().first()
        return progress.enrolled_version if progress else None

    def _get_snapshot(self, course_id: str, version_number: int) -> Optional[dict]:
        """Return the snapshot_json for a specific course version."""
        version = self.db.execute(
            select(CourseVersion).where(
                CourseVersion.course_id == course_id,
                CourseVersion.version_number == version_number
            )
        ).scalars().first()
        if not version or not version.snapshot_json:
            return None
        return version.snapshot_json

    def _resolve_asset_url(self, media_asset_id: int, org_id: int) -> str | None:
        """Resolve the actual URL for a media asset."""
        if not media_asset_id:
            return None
        asset = self.db.execute(
            select(MediaAsset).where(
                MediaAsset.id == media_asset_id,
                MediaAsset.org_id == org_id,
                MediaAsset.deleted_at.is_(None)
            )
        ).scalar_one_or_none()
        if not asset:
            return None
        # Return the storage_key if it's a local upload, otherwise return the URL
        if asset.storage_key.startswith("/uploads/"):
            return asset.storage_key
        return asset.url

    def get_block(self, user_id: str, course_id: str, block_id: int, org_id: int) -> Dict[str, Any]:
        """
        Retrieves the version-frozen block for the learner based on their enrolled version.
        Falls back to live Draft if the user is an author previewing without an enrollment.
        Raises ValueError if the block is not found.
        """
        enrolled_version = self._get_enrolled_version(user_id, course_id)

        # Draft Fallback
        if not enrolled_version:
            block = self.db.execute(
                select(LessonBlock).where(LessonBlock.id == block_id)
            ).scalars().first()
            if not block:
                raise ValueError("Block not found in Draft")
            settings = block.metadata_json or {}
            # Resolve asset URL for media blocks
            if block.media_asset_id:
                asset_url = self._resolve_asset_url(block.media_asset_id, org_id)
                if asset_url:
                    settings["url"] = asset_url
            return {
                "id": block.id,
                "module_id": block.module_id,
                "block_type": block.block_type,
                "content": block.content,
                "media_asset_id": block.media_asset_id,
                "metadata_json": settings,
                "settings": settings,
                "sort_order": block.sort_order,
            }

        # Retrieve CourseVersion snapshot
        snapshot = self._get_snapshot(course_id, enrolled_version)
        if not snapshot:
            raise ValueError("Enrolled CourseVersion or snapshot not found")

        # Traverse snapshot to find the block
        for section in snapshot.get("sections", []):
            for module in section.get("modules", []):
                for b in module.get("blocks", []):
                    if b.get("id") == block_id:
                        # Normalize settings
                        settings = b.get("metadata_json") or b.get("settings") or {}
                        # Resolve asset URL for media blocks
                        if b.get("media_asset_id"):
                            asset_url = self._resolve_asset_url(b.get("media_asset_id"), org_id)
                            if asset_url:
                                settings["url"] = asset_url
                        b["settings"] = settings
                        b["metadata_json"] = settings
                        return b

        raise ValueError(f"Block {block_id} not found in Snapshot V{enrolled_version}")

    def get_module(self, user_id: str, course_id: str, module_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a version-frozen module for the learner.
        Falls back to live Draft if no enrolled version.
        """
        enrolled_version = self._get_enrolled_version(user_id, course_id)

        if not enrolled_version:
            from app.models.course_module import CourseModule
            module = self.db.execute(
                select(CourseModule).where(CourseModule.id == module_id)
            ).scalars().first()
            if not module:
                return None
            return module.to_dict()

        snapshot = self._get_snapshot(course_id, enrolled_version)
        if not snapshot:
            return None

        for section in snapshot.get("sections", []):
            for mod in section.get("modules", []):
                if mod.get("id") == module_id:
                    return mod

        return None

    def get_all_modules(self, user_id: str, course_id: str) -> List[Dict[str, Any]]:
        """
        Returns all modules for the learner's enrolled version.
        Falls back to live Draft if no enrolled version.
        """
        enrolled_version = self._get_enrolled_version(user_id, course_id)

        if not enrolled_version:
            from app.models.course_module import CourseModule
            modules = self.db.execute(
                select(CourseModule).where(
                    CourseModule.course_id == course_id,
                    CourseModule.deleted_at.is_(None),
                ).order_by(CourseModule.sort_order)
            ).scalars().all()
            return [m.to_dict() for m in modules]

        snapshot = self._get_snapshot(course_id, enrolled_version)
        if not snapshot:
            return []

        modules = []
        for section in snapshot.get("sections", []):
            for mod in section.get("modules", []):
                modules.append(mod)
        return modules
