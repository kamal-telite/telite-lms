from __future__ import annotations

from collections import Counter
from typing import Any

from app.integrations.moodle_bridge import moodle_get_categories, moodle_get_site_info, moodle_get_users
from app.services.store import get_system_settings, initials, list_categories, list_users, slugify


CATEGORY_COLORS = ["#2563EB", "#7C3AED", "#059669", "#D97706", "#0EA5E9", "#F43F5E"]


def _color(index: int) -> str:
    return CATEGORY_COLORS[index % len(CATEGORY_COLORS)]


def _match_local_user(moodle_user: dict[str, Any], local_users: list[dict[str, Any]]) -> dict[str, Any] | None:
    username = str(moodle_user.get("username") or "").strip().lower()
    email = str(moodle_user.get("email") or "").strip().lower()
    for user in local_users:
        if str(user.get("username") or "").strip().lower() == username:
            return user
        if email and str(user.get("email") or "").strip().lower() == email:
            return user
    return None


def _normalize_moodle_user(
    moodle_user: dict[str, Any],
    local_users: list[dict[str, Any]],
    index: int,
) -> dict[str, Any]:
    local_user = _match_local_user(moodle_user, local_users)
    fallback_gradient = [_color(index), _color(index + 1)]
    local_gradient = local_user.get("avatar_gradient") if local_user else None
    gradient = (
        local_gradient
        if isinstance(local_gradient, list) and len(local_gradient) == 2
        else fallback_gradient
    )
    full_name = str(moodle_user.get("fullname") or "").strip()
    if not full_name:
        first_name = str(moodle_user.get("firstname") or "").strip()
        last_name = str(moodle_user.get("lastname") or "").strip()
        full_name = f"{first_name} {last_name}".strip() or str(moodle_user.get("username") or "")

    return {
        "id": f"moodle-user-{moodle_user['id']}",
        "moodle_user_id": moodle_user["id"],
        "username": moodle_user.get("username"),
        "email": moodle_user.get("email"),
        "full_name": full_name,
        "role": local_user["role"] if local_user else "moodle_user",
        "category_scope": local_user.get("category_scope") if local_user else None,
        "avatar_initials": (
            (local_user.get("avatar_initials") or initials(full_name))
            if local_user
            else initials(full_name)
        ),
        "avatar_gradient": gradient,
        "is_active": bool(moodle_user.get("confirmed", True)) and not bool(moodle_user.get("suspended", False)),
        "pal_score": None,
        "synced_to_telite": bool(local_user),
        "last_login": local_user.get("last_login") if local_user else None,
        "source": "moodle",
    }


def build_moodle_user_directory(
    *,
    role: str | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    local_users = list_users(include_inactive=True)["users"]
    moodle_users = moodle_get_users()
    normalized = [
        _normalize_moodle_user(moodle_user, local_users, index)
        for index, moodle_user in enumerate(moodle_users)
    ]

    if role:
        normalized = [user for user in normalized if user["role"] == role]

    if query:
        query_lower = query.lower()
        normalized = [
            user
            for user in normalized
            if query_lower in f"{user['full_name']} {user['email']} {user['username']}".lower()
        ]

    role_order = {"super_admin": 0, "category_admin": 1, "learner": 2, "moodle_user": 3}
    normalized.sort(key=lambda user: (role_order.get(user["role"], 4), user["full_name"].lower()))

    total = len(normalized)
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    return {
        "users": normalized[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "source": "moodle",
    }


def _match_moodle_category(local_category: dict[str, Any], moodle_categories: list[dict[str, Any]]) -> dict[str, Any] | None:
    local_slug = str(local_category.get("slug") or "").strip().lower()
    local_name = str(local_category.get("name") or "").strip().lower()
    for category in moodle_categories:
        category_name = str(category.get("name") or "").strip().lower()
        category_idnumber = str(category.get("idnumber") or "").strip().lower()
        if category_idnumber == local_slug:
            return category
        if category_name == local_name:
            return category
        if slugify(category_name) == local_slug:
            return category
    return None


def build_super_admin_dashboard_from_moodle() -> dict[str, Any]:
    local_categories = list_categories(include_archived=False)
    moodle_categories = moodle_get_categories()
    all_users = build_moodle_user_directory(page=1, page_size=5000)["users"]
    learner_counts = Counter(
        user["category_scope"]
        for user in all_users
        if user["role"] == "learner" and user.get("category_scope")
    )

    categories: list[dict[str, Any]] = []
    for index, local_category in enumerate(local_categories):
        moodle_category = _match_moodle_category(local_category, moodle_categories)
        is_synced = moodle_category is not None
        category_color = local_category.get("accent_color") or _color(index)
        categories.append(
            {
                **local_category,
                "accent_color": category_color,
                "total_courses": int(moodle_category.get("coursecount") or 0) if moodle_category else 0,
                "total_learners": learner_counts.get(local_category["slug"], 0),
                "avg_pal": 0,
                "admin_name": local_category.get("admin_name") or "Managed in Telite",
                "sync_status": "synced" if is_synced else "not_synced",
                "is_synced": is_synced,
                "moodle_category_id": moodle_category.get("id") if moodle_category else None,
                "moodle_path": moodle_category.get("path") if moodle_category else None,
            }
        )

    active_users = sum(1 for user in all_users if user["is_active"])
    inactive_users = max(len(all_users) - active_users, 0)
    synced_categories = sum(1 for category in categories if category["is_synced"])
    course_distribution = [
        {
            "category": category["name"],
            "value": category["total_courses"],
            "color": category["accent_color"] or _color(index),
        }
        for index, category in enumerate(categories)
    ]

    admins = [user for user in all_users if user["role"] in {"super_admin", "category_admin"}]

    return {
        "data_source": "moodle",
        "kpis": {
            "total_categories": len(categories),
            "total_courses": sum(category["total_courses"] for category in categories),
            "total_learners": active_users,
            "pending_approvals": 0,
        },
        "sync_summary": {
            "synced_categories": synced_categories,
            "unsynced_categories": max(len(categories) - synced_categories, 0),
            "moodle_users": len(all_users),
        },
        "categories": categories,
        "leaderboard": [],
        "admins": admins,
        "users": all_users,
        "enrollment_audit": {
            "rows": [],
            "visible_pending_ids": [],
        },
        "audit_log": [],
        "tasks": [],
        "analytics": {
            "learners_per_category": [
                {"category": "Active", "value": active_users, "color": "#2563EB"},
                {"category": "Inactive", "value": inactive_users, "color": "#94A3B8"},
            ],
            "avg_pal_per_category": [],
            "courses_per_category": course_distribution,
            "user_status_distribution": [
                {"category": "Active", "value": active_users, "color": "#2563EB"},
                {"category": "Inactive", "value": inactive_users, "color": "#94A3B8"},
            ],
        },
        "notes": {
            "admins": "Admin roles are shown only for accounts already synced into the Telite app.",
            "analytics": "Analytics below use only live Moodle category and account data.",
            "audit": "The current Moodle web-service token does not expose audit log entries.",
            "enrollment": "The current Moodle web-service token does not expose enrollment approval queues.",
            "pal": "PAL performance data is not exposed by the current Moodle web-service token.",
            "tasks": "Task assignments are stored locally and are hidden in Moodle-only mode.",
        },
    }


def build_moodle_settings_snapshot() -> dict[str, Any]:
    settings = get_system_settings()
    site_info = moodle_get_site_info()
    categories = moodle_get_categories()
    return {
        **settings,
        "data_source": "moodle",
        "moodle_url": site_info.get("siteurl") or settings["moodle_url"],
        "api_version": site_info.get("version") or settings["api_version"],
        "moodle_release": site_info.get("release"),
        "moodle_site_name": site_info.get("sitename"),
        "moodle_category_count": len(categories),
        "service_functions": [item["name"] for item in site_info.get("functions", []) if item.get("name")],
    }
