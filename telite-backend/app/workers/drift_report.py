"""
Moodle drift comparison engine — Phase 5.

Compares Telite DB state against live Moodle read APIs to detect drift:
  - Users that exist in Telite but not in Moodle (stale refs)
  - Users in Moodle with no Telite match (orphans)
  - Courses mismatched between systems
  - Enrollment discrepancies
  - Category structure differences

This module is used by reconciliation.py to build drift reports
and by the moodle_sync.py API to serve drift data to platform admins.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("telite.workers.drift")


# ── Data models ──────────────────────────────────────────────────────────────


@dataclass
class DriftItem:
    """A single drift finding between Telite and Moodle."""

    entity_type: str          # "user" | "course" | "enrollment" | "category"
    drift_type: str           # "missing_in_moodle" | "stale_ref" | "orphan_in_moodle" | "missing_enrollment" | "extra_enrollment"
    telite_id: str | None     # Telite record ID
    moodle_id: int | None     # Moodle record ID
    description: str
    auto_fixable: bool = False
    fixed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DriftReport:
    """Complete drift comparison report for an organisation."""

    org_id: int
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    users: dict[str, int] = field(default_factory=lambda: {"synced": 0, "missing": 0, "stale": 0, "orphans": 0})
    courses: dict[str, int] = field(default_factory=lambda: {"synced": 0, "missing": 0, "stale": 0, "orphans": 0})
    enrollments: dict[str, int] = field(default_factory=lambda: {"synced": 0, "missing": 0, "extra": 0})
    categories: dict[str, int] = field(default_factory=lambda: {"synced": 0, "missing": 0, "stale": 0})
    auto_fixes_applied: int = 0
    issues_requiring_review: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def add_item(self, item: DriftItem) -> None:
        """Add a drift item and update summary counts."""
        self.details.append(item.to_dict())
        entity = item.entity_type + "s"  # "user" -> "users"
        summary = getattr(self, entity, None)
        if summary is None:
            return

        if item.drift_type in ("missing_in_moodle", "missing_enrollment"):
            key = "missing"
        elif item.drift_type == "stale_ref":
            key = "stale"
        elif item.drift_type in ("orphan_in_moodle", "extra_enrollment"):
            key = "orphans" if "orphans" in summary else "extra"
        else:
            key = "missing"

        summary[key] = summary.get(key, 0) + 1

        if item.auto_fixable:
            self.auto_fixes_applied += 1 if item.fixed else 0
        if not item.auto_fixable and not item.fixed:
            self.issues_requiring_review += 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Comparison functions ─────────────────────────────────────────────────────


def compare_users(
    telite_users: list[dict[str, Any]],
    moodle_users: list[dict[str, Any]],
) -> list[DriftItem]:
    """
    Compare Telite users against Moodle users.

    telite_users: list of dicts with keys: id, username, email, moodle_id
    moodle_users: list of dicts from Moodle API with keys: id, username, email
    """
    items: list[DriftItem] = []

    # Index Moodle users by ID for O(1) lookup
    moodle_by_id: dict[int, dict] = {int(u["id"]): u for u in moodle_users}
    moodle_by_username: dict[str, dict] = {
        str(u.get("username", "")).lower(): u for u in moodle_users
    }
    matched_moodle_ids: set[int] = set()

    for tu in telite_users:
        moodle_id = tu.get("moodle_id")

        if not moodle_id:
            # Missing sync — user never synced to Moodle
            items.append(DriftItem(
                entity_type="user",
                drift_type="missing_in_moodle",
                telite_id=str(tu["id"]),
                moodle_id=None,
                description=f"User '{tu.get('username', tu['id'])}' has no moodle_id — never synced",
                auto_fixable=True,
            ))
            continue

        moodle_id = int(moodle_id)
        if moodle_id in moodle_by_id:
            # Successfully synced — record is consistent
            matched_moodle_ids.add(moodle_id)
        else:
            # Stale ref — moodle_id points to non-existent user
            items.append(DriftItem(
                entity_type="user",
                drift_type="stale_ref",
                telite_id=str(tu["id"]),
                moodle_id=moodle_id,
                description=f"User '{tu.get('username', tu['id'])}' has moodle_id={moodle_id} but user not found in Moodle",
                auto_fixable=True,
            ))

    # Detect orphans — users in Moodle with no Telite match
    telite_usernames = {str(u.get("username", "")).lower() for u in telite_users}
    for mu in moodle_users:
        mu_id = int(mu["id"])
        mu_username = str(mu.get("username", "")).lower()
        if mu_id not in matched_moodle_ids and mu_username not in telite_usernames:
            if mu_username in ("guest", "admin"):
                continue  # Skip Moodle system users
            items.append(DriftItem(
                entity_type="user",
                drift_type="orphan_in_moodle",
                telite_id=None,
                moodle_id=mu_id,
                description=f"Moodle user '{mu.get('username', mu_id)}' (id={mu_id}) has no matching Telite user",
                auto_fixable=False,
            ))

    return items


def compare_courses(
    telite_courses: list[dict[str, Any]],
    moodle_courses: list[dict[str, Any]],
) -> list[DriftItem]:
    """
    Compare Telite courses against Moodle courses.

    telite_courses: list of dicts with keys: id, name, moodle_course_id
    moodle_courses: list of dicts from Moodle API with keys: id, fullname
    """
    items: list[DriftItem] = []

    moodle_by_id: dict[int, dict] = {int(c["id"]): c for c in moodle_courses}
    matched_moodle_ids: set[int] = set()

    for tc in telite_courses:
        moodle_course_id = tc.get("moodle_course_id")

        if not moodle_course_id:
            items.append(DriftItem(
                entity_type="course",
                drift_type="missing_in_moodle",
                telite_id=str(tc["id"]),
                moodle_id=None,
                description=f"Course '{tc.get('name', tc['id'])}' has no moodle_course_id — never synced",
                auto_fixable=True,
            ))
            continue

        moodle_course_id = int(moodle_course_id)
        if moodle_course_id in moodle_by_id:
            matched_moodle_ids.add(moodle_course_id)
        else:
            items.append(DriftItem(
                entity_type="course",
                drift_type="stale_ref",
                telite_id=str(tc["id"]),
                moodle_id=moodle_course_id,
                description=f"Course '{tc.get('name', tc['id'])}' has moodle_course_id={moodle_course_id} but course not found in Moodle",
                auto_fixable=True,
            ))

    # Detect orphan courses in Moodle (not matched to any Telite course)
    telite_moodle_ids = {
        int(c["moodle_course_id"]) for c in telite_courses
        if c.get("moodle_course_id")
    }
    for mc in moodle_courses:
        mc_id = int(mc["id"])
        if mc_id == 1:
            continue  # Skip Moodle's default "Site" course (id=1)
        if mc_id not in matched_moodle_ids and mc_id not in telite_moodle_ids:
            items.append(DriftItem(
                entity_type="course",
                drift_type="orphan_in_moodle",
                telite_id=None,
                moodle_id=mc_id,
                description=f"Moodle course '{mc.get('fullname', mc_id)}' (id={mc_id}) has no matching Telite course",
                auto_fixable=False,
            ))

    return items


def compare_enrollments(
    telite_enrollments: list[dict[str, Any]],
    moodle_enrolled_user_ids: set[int],
    moodle_course_id: int,
    course_name: str = "",
) -> list[DriftItem]:
    """
    Compare Telite approved enrollments for a specific course against Moodle enrolled users.

    telite_enrollments: list of dicts with keys: id, user_id, moodle_user_id
    moodle_enrolled_user_ids: set of Moodle user IDs enrolled in this course
    """
    items: list[DriftItem] = []
    matched_moodle_ids: set[int] = set()

    for te in telite_enrollments:
        moodle_user_id = te.get("moodle_user_id") or te.get("moodle_id")
        if not moodle_user_id:
            continue  # User not yet synced — handled by user drift check

        moodle_user_id = int(moodle_user_id)
        if moodle_user_id in moodle_enrolled_user_ids:
            matched_moodle_ids.add(moodle_user_id)
        else:
            items.append(DriftItem(
                entity_type="enrollment",
                drift_type="missing_enrollment",
                telite_id=str(te.get("id", te.get("enrollment_id", ""))),
                moodle_id=moodle_user_id,
                description=(
                    f"User moodle_id={moodle_user_id} approved in Telite but not enrolled "
                    f"in Moodle course {moodle_course_id} ({course_name})"
                ),
                auto_fixable=True,
            ))

    # Extra enrollments — users in Moodle but not in Telite approved list
    telite_moodle_user_ids = {
        int(te.get("moodle_user_id") or te.get("moodle_id"))
        for te in telite_enrollments
        if te.get("moodle_user_id") or te.get("moodle_id")
    }
    for mu_id in moodle_enrolled_user_ids:
        if mu_id not in matched_moodle_ids and mu_id not in telite_moodle_user_ids:
            items.append(DriftItem(
                entity_type="enrollment",
                drift_type="extra_enrollment",
                telite_id=None,
                moodle_id=mu_id,
                description=(
                    f"Moodle user id={mu_id} enrolled in course {moodle_course_id} ({course_name}) "
                    f"but no matching Telite approval record"
                ),
                auto_fixable=False,
            ))

    return items


def compare_categories(
    telite_categories: list[dict[str, Any]],
    moodle_categories: list[dict[str, Any]],
) -> list[DriftItem]:
    """
    Compare Telite categories against Moodle categories.

    telite_categories: list of dicts with keys: id, name, slug, moodle_category_id
    moodle_categories: list of dicts from Moodle API with keys: id, name, idnumber
    """
    items: list[DriftItem] = []

    moodle_by_id: dict[int, dict] = {int(c["id"]): c for c in moodle_categories}

    for tc in telite_categories:
        moodle_cat_id = tc.get("moodle_category_id")

        if not moodle_cat_id:
            items.append(DriftItem(
                entity_type="category",
                drift_type="missing_in_moodle",
                telite_id=str(tc["id"]),
                moodle_id=None,
                description=f"Category '{tc.get('name', tc['id'])}' has no moodle_category_id — never synced",
                auto_fixable=True,
            ))
            continue

        moodle_cat_id = int(moodle_cat_id)
        if moodle_cat_id not in moodle_by_id:
            items.append(DriftItem(
                entity_type="category",
                drift_type="stale_ref",
                telite_id=str(tc["id"]),
                moodle_id=moodle_cat_id,
                description=f"Category '{tc.get('name', tc['id'])}' has moodle_category_id={moodle_cat_id} but category not found in Moodle",
                auto_fixable=True,
            ))

    return items
