"""
Moodle Web Services bridge — handles all communication with Moodle's REST API.

Key improvements over previous version:
- Structured logging (Python logging module instead of print)
- Retry logic with exponential backoff for transient failures
- MOODLE_INTERNAL_URL support for Docker service-to-service calls
- Detailed health check returning diagnostic info
- Proper error categorization for upstream consumers
"""
from __future__ import annotations

import hashlib
import logging
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("telite.moodle")


# ── Configuration helpers ────────────────────────────────────────────────────


def _get_moodle_url() -> str:
    """Return the Moodle base URL.

    Uses MOODLE_INTERNAL_URL (for Docker container-to-container) if set,
    otherwise falls back to MOODLE_URL (for host-based development).
    """
    internal = os.getenv("MOODLE_INTERNAL_URL", "").strip()
    if internal:
        return internal.rstrip("/")
    return os.getenv("MOODLE_URL", "http://localhost:8082").rstrip("/")


def _get_moodle_token() -> str:
    return os.getenv("MOODLE_TOKEN", "").strip()


def _rest_endpoint() -> str:
    return f"{_get_moodle_url()}/webservice/rest/server.php"


def moodle_mode() -> str:
    configured_mode = os.getenv("MOODLE_MODE", "auto").strip().lower()
    if configured_mode not in {"auto", "live", "mock"}:
        configured_mode = "auto"

    if configured_mode == "auto":
        return "live" if _get_moodle_token() else "mock"

    return configured_mode


# ── Mock ID generation ───────────────────────────────────────────────────────


def _mock_id(seed: str, minimum: int = 1000, span: int = 900000) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return minimum + (int(digest[:8], 16) % span)


# ── Core API caller with retry & structured logging ─────────────────────────

_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 2.0
_TOTAL_TIMEOUT_SECONDS = 25.0


def _call(function: str, *, _retries: int = _MAX_RETRIES, **params) -> dict:
    """Call a Moodle Web Service function.

    Returns dict with keys:
        data  — parsed JSON on success, None on failure
        error — error string on failure, None on success
    """
    payload = {
        "wstoken": _get_moodle_token(),
        "wsfunction": function,
        "moodlewsrestformat": "json",
        **params,
    }

    attempt = 0
    last_error: str | None = None
    call_start = time.time()

    while attempt <= _retries:
        # Guard: don't let total wall-clock time exceed the budget
        elapsed_total = time.time() - call_start
        if attempt > 0 and elapsed_total > _TOTAL_TIMEOUT_SECONDS:
            logger.error(
                "[MOODLE TIMEOUT BUDGET] function=%s total=%.1fs — aborting retries",
                function,
                elapsed_total,
            )
            break

        if attempt > 0:
            wait = min(_RETRY_BACKOFF_SECONDS * attempt, _TOTAL_TIMEOUT_SECONDS - elapsed_total)
            if wait <= 0:
                break
            logger.warning(
                "[MOODLE RETRY] function=%s attempt=%d/%d backoff=%.1fs",
                function,
                attempt,
                _retries,
                wait,
            )
            time.sleep(wait)

        try:
            logger.info("[MOODLE CALL] function=%s endpoint=%s", function, _rest_endpoint())
            response = httpx.post(_rest_endpoint(), data=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "exception" in data:
                error_msg = data.get("message", "Unknown Moodle error")
                logger.error(
                    "[MOODLE API ERROR] function=%s exception=%s message=%s",
                    function,
                    data.get("exception"),
                    error_msg,
                )
                return {"error": error_msg, "raw": data}

            logger.info("[MOODLE OK] function=%s (%.1fms)", function, (time.time() - call_start) * 1000)
            return {"data": data, "error": None}

        except httpx.ConnectError as exc:
            last_error = f"Connection refused: {exc}"
            logger.error("[MOODLE CONNECT ERROR] function=%s error=%s", function, last_error)
        except httpx.TimeoutException as exc:
            last_error = f"Timeout: {exc}"
            logger.error("[MOODLE TIMEOUT] function=%s error=%s", function, last_error)
        except httpx.RequestError as exc:
            last_error = f"Request error: {exc}"
            logger.error("[MOODLE REQUEST ERROR] function=%s error=%s", function, last_error)
        except Exception as exc:
            last_error = str(exc)
            logger.error("[MOODLE UNEXPECTED ERROR] function=%s error=%s", function, last_error)
            # Don't retry on unexpected errors (e.g. JSON decode)
            return {"error": last_error, "data": None}

        attempt += 1

    logger.error("[MOODLE EXHAUSTED] function=%s after %d retries: %s", function, _retries, last_error)
    return {"error": last_error, "data": None}


# ── Health check ─────────────────────────────────────────────────────────────


def moodle_health_check() -> bool:
    if moodle_mode() == "mock":
        return True

    result = _call("core_webservice_get_site_info", _retries=0)
    return result["error"] is None


def moodle_health_detail() -> dict:
    """Return detailed health info for the /moodle/health endpoint."""
    mode = moodle_mode()
    if mode == "mock":
        return {
            "status": "ok",
            "mode": "mock",
            "message": "Running in mock mode — no live Moodle connection.",
            "moodle_url": _get_moodle_url(),
            "token_configured": bool(_get_moodle_token()),
        }

    start = time.time()
    result = _call("core_webservice_get_site_info", _retries=0)
    elapsed_ms = round((time.time() - start) * 1000, 1)

    if result["error"]:
        return {
            "status": "error",
            "mode": mode,
            "moodle_url": _get_moodle_url(),
            "token_configured": bool(_get_moodle_token()),
            "error": result["error"],
            "response_time_ms": elapsed_ms,
        }

    data = result["data"] or {}
    return {
        "status": "ok",
        "mode": mode,
        "moodle_url": _get_moodle_url(),
        "token_configured": True,
        "site_name": data.get("sitename"),
        "moodle_version": data.get("version"),
        "moodle_release": data.get("release"),
        "username": data.get("username"),
        "functions_count": len(data.get("functions", [])),
        "response_time_ms": elapsed_ms,
    }


# ── User management ─────────────────────────────────────────────────────────


def moodle_create_user(
    username: str,
    password: str,
    firstname: str,
    lastname: str,
    email: str,
    custom_fields: dict | None = None,
) -> dict:
    if moodle_mode() == "mock":
        return {
            "success": True,
            "user_id": _mock_id(f"user:{username}", minimum=10000),
            "already_existed": False,
            "mock": True,
        }

    params = {
        "users[0][username]": username,
        "users[0][password]": password,
        "users[0][firstname]": firstname,
        "users[0][lastname]": lastname,
        "users[0][email]": email,
        "users[0][auth]": "manual",
    }

    if custom_fields:
        for index, (key, value) in enumerate(custom_fields.items()):
            params[f"users[0][customfields][{index}][type]"] = key
            params[f"users[0][customfields][{index}][value]"] = str(value)

    result = _call("core_user_create_users", **params)

    if result["error"]:
        err = str(result["error"]).lower()
        # Moodle returns InvalidParameterException for duplicates too
        if "already" in err or "username" in err or "invalid parameter" in err:
            existing = moodle_get_user_by_username(username)
            if existing:
                return {"success": True, "user_id": existing, "already_existed": True}
        return {"success": False, "error": result["error"]}

    users = result["data"]
    if users and isinstance(users, list):
        return {"success": True, "user_id": users[0]["id"], "already_existed": False}

    return {"success": False, "error": "Unexpected response from Moodle"}


def moodle_get_user_by_username(username: str) -> int | None:
    if moodle_mode() == "mock":
        return _mock_id(f"user:{username}", minimum=10000)

    result = _call(
        "core_user_get_users",
        **{
            "criteria[0][key]": "username",
            "criteria[0][value]": username,
        },
    )
    if result["error"]:
        return None

    users = result["data"].get("users", [])
    return users[0]["id"] if users else None


# ── Cohort management ────────────────────────────────────────────────────────


def moodle_get_cohort_id(cohort_idnumber: str) -> int | None:
    if moodle_mode() == "mock":
        return _mock_id(f"cohort:{cohort_idnumber}", minimum=500)

    result = _call("core_cohort_get_cohorts")

    if result["error"] or not result["data"]:
        return None

    for cohort in result["data"]:
        if cohort.get("idnumber", "").lower() == cohort_idnumber.lower():
            return cohort["id"]

    return None


def moodle_add_user_to_cohort(user_id: int, cohort_id: int) -> bool:
    if moodle_mode() == "mock":
        return True

    result = _call(
        "core_cohort_add_cohort_members",
        **{
            "members[0][cohorttype][type]": "id",
            "members[0][cohorttype][value]": str(cohort_id),
            "members[0][usertype][type]": "id",
            "members[0][usertype][value]": str(user_id),
        },
    )
    return result["error"] is None


# ── Enrollment ───────────────────────────────────────────────────────────────


def moodle_assign_teacher_to_course(user_id: int, course_id: int) -> bool:
    if moodle_mode() == "mock":
        return True

    teacher_role_id = int(os.getenv("MOODLE_TEACHER_ROLE_ID", "3"))

    result = _call(
        "enrol_manual_enrol_users",
        **{
            "enrolments[0][roleid]": str(teacher_role_id),
            "enrolments[0][userid]": str(user_id),
            "enrolments[0][courseid]": str(course_id),
        },
    )
    return result["error"] is None


def moodle_enrol_student(user_id: int, course_id: int) -> bool:
    if moodle_mode() == "mock":
        return True

    student_role_id = int(os.getenv("MOODLE_STUDENT_ROLE_ID", "5"))

    result = _call(
        "enrol_manual_enrol_users",
        **{
            "enrolments[0][roleid]": str(student_role_id),
            "enrolments[0][userid]": str(user_id),
            "enrolments[0][courseid]": str(course_id),
        },
    )
    return result["error"] is None


# ── Course / category queries ────────────────────────────────────────────────


def moodle_get_courses_in_category(category_id: int) -> list:
    if moodle_mode() == "mock":
        return [
            {
                "id": _mock_id(f"course-category:{category_id}", minimum=100),
                "fullname": f"Mock Course for Category {category_id}",
                "categoryid": category_id,
            }
        ]

    result = _call(
        "core_course_get_courses_by_field",
        **{
            "field": "category",
            "value": str(category_id),
        },
    )
    if result["error"]:
        return []

    return result["data"].get("courses", [])


def _normalize_key(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip())
    return "-".join(part for part in cleaned.split("-") if part)


def moodle_get_site_info() -> dict:
    if moodle_mode() == "mock":
        return {
            "sitename": "Telite LMS Platform",
            "siteurl": _get_moodle_url(),
            "version": "mock",
            "release": "mock",
            "functions": [],
        }

    result = _call("core_webservice_get_site_info")
    if result["error"] or not isinstance(result["data"], dict):
        return {}

    return result["data"]


def moodle_get_categories() -> list[dict]:
    if moodle_mode() == "mock":
        return []

    result = _call("core_course_get_categories")
    if result["error"] or not isinstance(result["data"], list):
        return []

    return result["data"]


def moodle_find_category(identifier: str, *, parent_id: int | None = None) -> dict | None:
    identifier_key = _normalize_key(identifier)
    for category in moodle_get_categories():
        if parent_id is not None and int(category.get("parent") or 0) != parent_id:
            continue
        category_name = str(category.get("name") or "")
        category_idnumber = str(category.get("idnumber") or "")
        if (
            _normalize_key(category_name) == identifier_key
            or _normalize_key(category_idnumber) == identifier_key
        ):
            return category
    return None


def moodle_get_category_by_id(category_id: int) -> dict | None:
    category_id = int(category_id)
    for category in moodle_get_categories():
        if int(category.get("id") or 0) == category_id:
            return category
    return None


def moodle_get_default_parent_category_id() -> int:
    configured_parent = os.getenv("MOODLE_PARENT_CATEGORY_ID", "").strip()
    if configured_parent.isdigit():
        return int(configured_parent)

    parent_name = os.getenv("MOODLE_PARENT_CATEGORY_NAME", "Telite Systems").strip()
    category = moodle_find_category(parent_name)
    if category:
        return int(category["id"])

    return 0


def moodle_create_category(
    name: str,
    *,
    slug: str | None = None,
    description: str = "",
    parent_id: int | None = None,
) -> dict:
    if moodle_mode() == "mock":
        return {
            "success": True,
            "category_id": _mock_id(f"category:{slug or name}", minimum=200),
            "already_existed": False,
            "mock": True,
        }

    resolved_parent = moodle_get_default_parent_category_id() if parent_id is None else int(parent_id)
    if slug:
        existing = moodle_find_category(slug, parent_id=resolved_parent)
        if existing:
            return {
                "success": True,
                "category_id": existing["id"],
                "already_existed": True,
                "category": existing,
            }

    existing_by_name = moodle_find_category(name, parent_id=resolved_parent)
    if existing_by_name:
        return {
            "success": True,
            "category_id": existing_by_name["id"],
            "already_existed": True,
            "category": existing_by_name,
        }

    params = {
        "categories[0][name]": name,
        "categories[0][parent]": str(resolved_parent),
        "categories[0][description]": description or "",
        "categories[0][descriptionformat]": "1",
    }
    if slug:
        params["categories[0][idnumber]"] = slug

    logger.info("[MOODLE CREATE CATEGORY] name=%s slug=%s parent=%d", name, slug, resolved_parent)
    result = _call("core_course_create_categories", **params)
    if result["error"]:
        logger.error("[MOODLE CREATE CATEGORY FAILED] name=%s error=%s", name, result["error"])
        return {"success": False, "error": result["error"]}

    data = result["data"]
    if isinstance(data, list) and data:
        created = data[0]
        logger.info("[MOODLE CATEGORY CREATED] name=%s moodle_id=%s", name, created.get("id"))
        return {
            "success": True,
            "category_id": created["id"],
            "already_existed": False,
            "category": created,
        }

    return {"success": False, "error": "Unexpected response from Moodle while creating category."}


# ── Course operations ────────────────────────────────────────────────────────


def moodle_create_course(name: str, category_id: int, shortname: str | None = None) -> dict:
    if moodle_mode() == "mock":
        return {
            "success": True,
            "course_id": _mock_id(f"course:{name}", minimum=300),
            "mock": True,
        }

    short_n = shortname or name.replace(" ", "_")
    params = {
        "courses[0][fullname]": name,
        "courses[0][shortname]": short_n,
        "courses[0][categoryid]": str(category_id),
    }

    logger.info("[MOODLE CREATE COURSE] name=%s category_id=%d", name, category_id)
    result = _call("core_course_create_courses", **params)
    if result["error"]:
        logger.error("[MOODLE CREATE COURSE FAILED] name=%s error=%s", name, result["error"])
        return {"success": False, "error": result["error"]}

    data = result["data"]
    if isinstance(data, list) and data:
        created = data[0]
        logger.info("[MOODLE COURSE CREATED] name=%s moodle_id=%s", name, created.get("id"))
        return {
            "success": True,
            "course_id": created["id"],
            "course": created,
        }

    return {"success": False, "error": "Unexpected response from Moodle while creating course."}


# ── Delete / suspend operations ──────────────────────────────────────────────


def moodle_delete_category(moodle_category_id: int) -> dict:
    """Delete a category from Moodle.

    Uses core_course_delete_categories.
    Returns {"success": True} or {"success": False, "error": "..."}.
    """
    if moodle_mode() == "mock":
        logger.info("[MOODLE MOCK] Delete category id=%d", moodle_category_id)
        return {"success": True, "mock": True}

    category = moodle_get_category_by_id(moodle_category_id)
    if not category:
        logger.info("[MOODLE DELETE CATEGORY] id=%d already missing upstream", moodle_category_id)
        return {"success": True, "already_deleted": True}

    params = {
        "categories[0][id]": str(moodle_category_id),
    }
    parent_id = int(category.get("parent") or 0)
    default_parent_id = moodle_get_default_parent_category_id()
    if parent_id > 0:
        params["categories[0][newparent]"] = str(parent_id)
    elif default_parent_id > 0 and default_parent_id != int(moodle_category_id):
        params["categories[0][newparent]"] = str(default_parent_id)
    else:
        return {
            "success": False,
            "error": (
                "Cannot delete a top-level Moodle category because there is no valid "
                "parent category available to move its contents into."
            ),
        }

    logger.info(
        "[MOODLE DELETE CATEGORY] id=%d move_target=%s",
        moodle_category_id,
        params.get("categories[0][newparent]"),
    )
    result = _call(
        "core_course_delete_categories",
        **params,
    )
    if result["error"]:
        logger.error("[MOODLE DELETE CATEGORY FAILED] id=%d error=%s", moodle_category_id, result["error"])
        return {"success": False, "error": result["error"]}

    logger.info("[MOODLE CATEGORY DELETED] id=%d", moodle_category_id)
    return {"success": True}


def moodle_delete_courses(moodle_course_ids: list[int]) -> dict:
    """Delete one or more courses from Moodle.

    Uses core_course_delete_courses.
    Returns {"success": True} or {"success": False, "error": "..."}.
    """
    if moodle_mode() == "mock":
        logger.info("[MOODLE MOCK] Delete courses ids=%s", moodle_course_ids)
        return {"success": True, "mock": True}

    if not moodle_course_ids:
        return {"success": True}

    params = {}
    for index, cid in enumerate(moodle_course_ids):
        params[f"courseids[{index}]"] = str(cid)

    logger.info("[MOODLE DELETE COURSES] ids=%s", moodle_course_ids)
    result = _call("core_course_delete_courses", **params)

    if result["error"]:
        logger.error(
            "[MOODLE DELETE COURSES FAILED] ids=%s error=%s",
            moodle_course_ids,
            result["error"],
        )
        return {"success": False, "error": result["error"]}

    logger.info("[MOODLE COURSES DELETED] ids=%s", moodle_course_ids)
    return {"success": True}


def moodle_suspend_user(moodle_user_id: int) -> dict:
    """Suspend (soft-delete) a user in Moodle.

    Moodle's REST API doesn't support hard-deleting users.
    Instead we set suspended=1 via core_user_update_users.
    Returns {"success": True} or {"success": False, "error": "..."}.
    """
    if moodle_mode() == "mock":
        logger.info("[MOODLE MOCK] Suspend user id=%d", moodle_user_id)
        return {"success": True, "mock": True}

    logger.info("[MOODLE SUSPEND USER] id=%d", moodle_user_id)
    result = _call(
        "core_user_update_users",
        **{
            "users[0][id]": str(moodle_user_id),
            "users[0][suspended]": "1",
        },
    )

    if result["error"]:
        logger.error(
            "[MOODLE SUSPEND USER FAILED] id=%d error=%s",
            moodle_user_id,
            result["error"],
        )
        return {"success": False, "error": result["error"]}

    logger.info("[MOODLE USER SUSPENDED] id=%d", moodle_user_id)
    return {"success": True}


# ── User directory ───────────────────────────────────────────────────────────


def moodle_get_users() -> list[dict]:
    if moodle_mode() == "mock":
        return []

    result = _call(
        "core_user_get_users",
        **{
            "criteria[0][key]": "email",
            "criteria[0][value]": "%",
        },
    )
    if result["error"] or not isinstance(result["data"], dict):
        return []

    users = result["data"].get("users", [])
    return [user for user in users if str(user.get("username") or "").lower() != "guest"]
