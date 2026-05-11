from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
from app.data.seed_data import ATS_STATS_CONFIG, build_seed_payload

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when psycopg is unavailable.
    psycopg = None
    dict_row = None


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger("telite.store")

DB_BACKEND_SQLITE = "sqlite"
DB_BACKEND_POSTGRES = "postgres"
POSTGRES_PREFIXES = ("postgres://", "postgresql://", "psql://")
VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
POSTGRES_SEQUENCE_TABLES = (
    "activity_log",
    "admin_actions",
    "allowed_domains",
    "audit_log",
    "moodle_tenants",
    "notifications",
    "org_feature_flags",
    "org_invitations",
    "organizations",
    "password_reset_tokens",
)
SQLITE_TO_POSTGRES_TABLE_ORDER = (
    "organizations",
    "org_feature_flags",
    "moodle_tenants",
    "users",
    "categories",
    "courses",
    "enrollment_requests",
    "tasks",
    "audit_log",
    "activity_log",
    "notifications",
    "allowed_domains",
    "auth_sessions",
    "password_reset_tokens",
    "pending_verifications",
    "admin_actions",
    "org_invitations",
)


class CompatCursor:
    def __init__(self, raw_cursor: Any):
        self._raw_cursor = raw_cursor

    def fetchone(self):
        return self._raw_cursor.fetchone()

    def fetchall(self):
        return self._raw_cursor.fetchall()

    def __iter__(self):
        return iter(self._raw_cursor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_cursor, name)


class CompatConnection:
    def __init__(self, raw_connection: Any, backend: str):
        self._raw_connection = raw_connection
        self.backend = backend

    def execute(self, query: str, params: list[Any] | tuple[Any, ...] | None = None) -> CompatCursor:
        prepared = _prepare_query(query, self.backend)
        if params is None:
            return CompatCursor(self._raw_connection.execute(prepared))
        return CompatCursor(self._raw_connection.execute(prepared, params))

    def executemany(self, query: str, rows: list[tuple[Any, ...]] | tuple[tuple[Any, ...], ...]):
        prepared = _prepare_query(query, self.backend)
        if hasattr(self._raw_connection, "executemany"):
            return self._raw_connection.executemany(prepared, rows)
        cursor = self._raw_connection.cursor()
        try:
            cursor.executemany(prepared, rows)
        finally:
            cursor.close()

    def executescript(self, script: str) -> None:
        if self.backend == DB_BACKEND_SQLITE:
            self._raw_connection.executescript(script)
            return
        for statement in _iter_sql_statements(_postgresize_schema_sql(script)):
            self._raw_connection.execute(statement)

    def cursor(self) -> CompatCursor:
        return CompatCursor(self._raw_connection.cursor())

    def commit(self) -> None:
        self._raw_connection.commit()

    def rollback(self) -> None:
        self._raw_connection.rollback()

    def close(self) -> None:
        self._raw_connection.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_connection, name)


TENANT_SUPER_ADMIN_ROLES = frozenset({"super_admin"})
CATEGORY_ADMIN_ROLES = frozenset({"category_admin"})
LEARNER_ROLES = frozenset({"learner"})
ADMIN_ROLES = frozenset(TENANT_SUPER_ADMIN_ROLES | CATEGORY_ADMIN_ROLES)
ROLE_NORMALIZATION_ALIASES = {
    "college_super_admin": "super_admin",
    "company_super_admin": "super_admin",
    "college_admin": "super_admin",
    "company_admin": "super_admin",
    "teacher": "category_admin",
    "project_admin": "category_admin",
    "admin": "category_admin",
    "student": "learner",
    "employee": "learner",
    "intern": "learner",
}
ALL_SUPPORTED_ROLES = frozenset(ADMIN_ROLES | LEARNER_ROLES | frozenset(ROLE_NORMALIZATION_ALIASES))
ROLE_FILTER_ALIASES = {
    "super_admin": TENANT_SUPER_ADMIN_ROLES,
    "category_admin": CATEGORY_ADMIN_ROLES,
    "learner": LEARNER_ROLES,
}
SQL_TENANT_SUPER_ADMIN_ROLES = ", ".join(f"'{role}'" for role in sorted(TENANT_SUPER_ADMIN_ROLES))
SQL_CATEGORY_ADMIN_ROLES = ", ".join(f"'{role}'" for role in sorted(CATEGORY_ADMIN_ROLES))
SQL_LEARNER_ROLES = ", ".join(f"'{role}'" for role in sorted(LEARNER_ROLES))
SQL_ADMIN_ROLES = ", ".join(f"'{role}'" for role in sorted(ADMIN_ROLES))


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _prepare_query(query: str, backend: str) -> str:
    if backend == DB_BACKEND_POSTGRES:
        return query.replace("?", "%s")
    return query


def _iter_sql_statements(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _postgresize_schema_sql(script: str) -> str:
    return script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")


def _postgres_configured() -> bool:
    return bool(
        os.getenv("TELITE_POSTGRES_DB")
        or os.getenv("TELITE_POSTGRES_HOST")
        or os.getenv("TELITE_DATABASE_URL")
        or os.getenv("MOODLE_DB_NAME")
        or os.getenv("POSTGRES_DB")
    )


def get_db_backend() -> str:
    explicit = os.getenv("TELITE_DB_BACKEND", "").strip().lower()
    if explicit in {DB_BACKEND_SQLITE, DB_BACKEND_POSTGRES}:
        return explicit

    database_url = os.getenv("TELITE_DATABASE_URL", "").strip()
    if database_url:
        if database_url.lower().startswith(POSTGRES_PREFIXES):
            return DB_BACKEND_POSTGRES
        return DB_BACKEND_SQLITE

    if os.getenv("TELITE_DB_PATH", "").strip():
        return DB_BACKEND_SQLITE

    if _postgres_configured():
        return DB_BACKEND_POSTGRES

    return DB_BACKEND_SQLITE


def get_db_path() -> str:
    env_path = os.getenv("TELITE_DB_PATH", "").strip()
    if env_path:
        return env_path
    return str(DATA_DIR / "telite_lms.db")


def get_postgres_dsn() -> str:
    env_url = os.getenv("TELITE_DATABASE_URL", "").strip()
    if env_url:
        return env_url

    host = (
        os.getenv("TELITE_POSTGRES_HOST")
        or os.getenv("MOODLE_DB_HOST")
        or os.getenv("POSTGRES_HOST")
        or "localhost"
    )
    port = (
        os.getenv("TELITE_POSTGRES_PORT")
        or os.getenv("MOODLE_DB_PORT")
        or os.getenv("POSTGRES_PORT")
        or "5432"
    )
    database = os.getenv("TELITE_POSTGRES_DB") or os.getenv("MOODLE_DB_NAME") or os.getenv("POSTGRES_DB")
    user = os.getenv("TELITE_POSTGRES_USER") or os.getenv("MOODLE_DB_USER") or os.getenv("POSTGRES_USER")
    password = (
        os.getenv("TELITE_POSTGRES_PASSWORD")
        or os.getenv("MOODLE_DB_PASSWORD")
        or os.getenv("POSTGRES_PASSWORD")
    )

    if not all([database, user, password]):
        raise RuntimeError(
            "PostgreSQL backend selected but credentials are incomplete. "
            "Set TELITE_DATABASE_URL or the TELITE_POSTGRES_* variables."
        )

    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"


def _connect() -> CompatConnection:
    backend = get_db_backend()
    if backend == DB_BACKEND_POSTGRES:
        if psycopg is None or dict_row is None:
            raise RuntimeError(
                "PostgreSQL backend selected but psycopg is not installed. "
                "Add 'psycopg[binary]' to the environment."
            )
        raw_connection = psycopg.connect(get_postgres_dsn(), row_factory=dict_row, autocommit=False)
        return CompatConnection(raw_connection, DB_BACKEND_POSTGRES)

    raw_connection = sqlite3.connect(get_db_path())
    raw_connection.row_factory = sqlite3.Row
    return CompatConnection(raw_connection, DB_BACKEND_SQLITE)


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def _json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts)


def initials(full_name: str) -> str:
    parts = [part for part in full_name.split() if part]
    return "".join(part[0] for part in parts[:2]).upper()


def hash_password(password: str) -> str:
    salt = os.getenv("TELITE_PASSWORD_SALT", "telite-dev-salt").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000).hex()


def verify_password(password: str, hashed_value: str) -> bool:
    return hash_password(password) == hashed_value


def _canonical_role(role: str | None) -> str:
    normalized = (role or "").strip().lower()
    return ROLE_NORMALIZATION_ALIASES.get(normalized, normalized)


def normalize_role(role: str) -> str:
    normalized = _canonical_role(role)
    if normalized not in ALL_SUPPORTED_ROLES:
        raise ValueError(f"Unsupported role '{role}'.")
    return normalized


def is_tenant_super_admin_role(role: str | None) -> bool:
    return _canonical_role(role) in TENANT_SUPER_ADMIN_ROLES


def is_category_admin_role(role: str | None) -> bool:
    return _canonical_role(role) in CATEGORY_ADMIN_ROLES


def is_learner_role(role: str | None) -> bool:
    return _canonical_role(role) in LEARNER_ROLES


def is_admin_role(role: str | None) -> bool:
    return _canonical_role(role) in ADMIN_ROLES


def expand_role_filter(role: str | None) -> tuple[str, ...]:
    if role is None:
        return ()
    normalized = _canonical_role(role)
    if normalized in ROLE_FILTER_ALIASES:
        return tuple(sorted(ROLE_FILTER_ALIASES[normalized]))
    return (normalized,)


def role_priority(role: str | None) -> int:
    normalized = _canonical_role(role)
    if is_tenant_super_admin_role(normalized):
        return 0
    if is_category_admin_role(normalized):
        return 1
    if is_learner_role(normalized):
        return 2
    return 3


def role_gradients(role: str | None) -> tuple[str, str]:
    normalized = _canonical_role(role)
    if is_tenant_super_admin_role(normalized):
        return "#7C3AED", "#2563EB"
    if is_category_admin_role(normalized):
        return "#2563EB", "#0891B2"
    return "#059669", "#0891B2"


def _connection_backend(conn: Any) -> str:
    return getattr(conn, "backend", DB_BACKEND_SQLITE)


def _safe_identifier(identifier: str) -> str:
    if not VALID_IDENTIFIER.match(identifier):
        raise ValueError(f"Unsafe identifier: {identifier}")
    return identifier


def get_table_columns(conn: Any, table: str) -> list[str]:
    table_name = _safe_identifier(table)
    if _connection_backend(conn) == DB_BACKEND_POSTGRES:
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,),
        ).fetchall()
        return [row["column_name"] for row in rows]
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def _row_to_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return record
    return dict(record)


def _exec_many(conn: Any, query: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        conn.executemany(query, rows)


def _extract_org_id(record: dict[str, Any] | sqlite3.Row | None) -> int | None:
    if record is None:
        return None
    item = _row_to_dict(record)
    if item.get("org_id") is not None:
        return int(item["org_id"])
    if item.get("organization_id") is not None:
        return int(item["organization_id"])
    return None


def _lookup_category_org_id(conn: sqlite3.Connection, category_slug: str | None) -> int | None:
    if not category_slug or category_slug == "all":
        return None
    row = conn.execute(
        "SELECT org_id, organization_id FROM categories WHERE slug = ? LIMIT 1",
        (category_slug,),
    ).fetchone()
    return _extract_org_id(row)


def _sync_org_context(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE users SET org_id = COALESCE(organization_id, org_id, 1)")
    conn.execute("UPDATE users SET organization_id = COALESCE(organization_id, org_id, 1)")
    conn.execute("UPDATE categories SET org_id = COALESCE(org_id, organization_id, 1)")
    conn.execute("UPDATE categories SET organization_id = COALESCE(organization_id, org_id, 1)")
    conn.execute(
        """
        UPDATE courses
        SET org_id = COALESCE(
            (SELECT COALESCE(c.org_id, c.organization_id, 1) FROM categories c WHERE c.slug = courses.category_slug),
            org_id,
            1
        )
        """
    )
    conn.execute(
        """
        UPDATE enrollment_requests
        SET org_id = COALESCE(
            (SELECT COALESCE(c.org_id, c.organization_id, 1) FROM categories c WHERE c.slug = enrollment_requests.category_slug),
            org_id,
            1
        )
        """
    )


def _normalize_existing_roles(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE users
        SET role = 'super_admin'
        WHERE role IN ('college_super_admin', 'company_super_admin', 'college_admin', 'company_admin')
        """
    )
    conn.execute(
        """
        UPDATE users
        SET role = 'category_admin'
        WHERE role IN ('teacher', 'project_admin', 'admin')
        """
    )
    conn.execute(
        """
        UPDATE users
        SET role = 'learner'
        WHERE role IN ('student', 'employee', 'intern')
        """
    )
    conn.execute(
        """
        UPDATE org_invitations
        SET role = 'super_admin'
        WHERE role IN ('college_super_admin', 'company_super_admin', 'college_admin', 'company_admin')
        """
    )
    conn.execute(
        """
        UPDATE org_invitations
        SET role = 'category_admin'
        WHERE role IN ('teacher', 'project_admin', 'admin')
        """
    )
    conn.execute(
        """
        UPDATE org_invitations
        SET role = 'learner'
        WHERE role IN ('student', 'employee', 'intern')
        """
    )


def _ensure_global_admin_seed(conn: sqlite3.Connection) -> None:
    now = now_local()
    existing = conn.execute(
        "SELECT id FROM users WHERE lower(username) = lower('globaladmin') LIMIT 1"
    ).fetchone()
    if not existing:
        conn.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, role, category_scope, password_hash,
                avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                pal_task_completion_pct, streak_days, courses_completed, total_courses,
                cohort_rank, enrollment_type, current_course_id, course_progress_json,
                created_at, last_login, organization_id, org_id, is_platform_admin, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "user-global-admin",
                "globaladmin",
                "globaladmin@telite.io",
                "Global Admin",
                "super_admin",
                None,
                hash_password("Global@1234"),
                "GA",
                "#7C3AED",
                "#2563EB",
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                None,
                "[]",
                now,
                None,
                1,
                1,
                1,
                "active",
            ),
        )
    conn.execute(
        """
        UPDATE users
        SET role = 'super_admin', is_platform_admin = 1, organization_id = COALESCE(organization_id, 1),
            org_id = COALESCE(org_id, organization_id, 1), status = COALESCE(status, 'active')
        WHERE lower(username) = lower('globaladmin')
        """
    )
    conn.execute(
        """
        UPDATE users
        SET is_platform_admin = 0, role = 'super_admin'
        WHERE lower(username) = lower('superadmin')
        """
    )


def init_db() -> None:
    if get_db_backend() == DB_BACKEND_SQLITE:
        os.makedirs(os.path.dirname(get_db_path()), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                category_scope TEXT,
                password_hash TEXT NOT NULL,
                avatar_initials TEXT NOT NULL,
                gradient_start TEXT NOT NULL,
                gradient_end TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                pal_score REAL NOT NULL DEFAULT 0,
                pal_completion_pct REAL NOT NULL DEFAULT 0,
                pal_quiz_avg REAL NOT NULL DEFAULT 0,
                pal_time_spent_hours REAL NOT NULL DEFAULT 0,
                pal_task_completion_pct REAL NOT NULL DEFAULT 0,
                streak_days INTEGER NOT NULL DEFAULT 0,
                courses_completed INTEGER NOT NULL DEFAULT 0,
                total_courses INTEGER NOT NULL DEFAULT 0,
                cohort_rank INTEGER,
                enrollment_type TEXT,
                current_course_id TEXT,
                course_progress_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                last_login TEXT,
                program TEXT,
                branch TEXT,
                id_number TEXT,
                moodle_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                accent_color TEXT NOT NULL,
                admin_user_id TEXT,
                planned_courses INTEGER NOT NULL DEFAULT 0,
                avg_pal_target REAL NOT NULL DEFAULT 0,
                moodle_category_id INTEGER,
                org_type TEXT NOT NULL DEFAULT 'college',
                organization_id INTEGER,
                created_at TEXT NOT NULL,
                archived_at TEXT
            );

            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                moodle_course_id INTEGER,
                category_slug TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                module_count INTEGER NOT NULL DEFAULT 0,
                modules_json TEXT NOT NULL DEFAULT '[]',
                lessons_count INTEGER NOT NULL DEFAULT 0,
                hours REAL NOT NULL DEFAULT 0,
                enrolled_count INTEGER NOT NULL DEFAULT 0,
                completion_rate REAL NOT NULL DEFAULT 0,
                completion_count INTEGER NOT NULL DEFAULT 0,
                avg_quiz_score REAL NOT NULL DEFAULT 0,
                prerequisite_course_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS enrollment_requests (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                category_slug TEXT NOT NULL,
                request_type TEXT NOT NULL,
                company_domain TEXT,
                domain_verified INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                rejection_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                assigned_label TEXT NOT NULL,
                assigned_to_user_id TEXT,
                assignment_scope TEXT NOT NULL,
                category_slug TEXT NOT NULL,
                due_at TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                assigned_by TEXT,
                notes TEXT,
                is_cross_category INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id TEXT,
                actor_name TEXT NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                message TEXT NOT NULL,
                accent TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                category_slug TEXT,
                icon TEXT NOT NULL,
                accent TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS allowed_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                added_by TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_verifications (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role_name TEXT NOT NULL,
                domain_type TEXT NOT NULL,
                organization_name TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                phone TEXT,
                employee_id TEXT,
                department TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                rejection_reason TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                moodle_id INTEGER,
                created_at TEXT NOT NULL,
                program TEXT,
                branch TEXT,
                id_number TEXT
            );

            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                domain TEXT NOT NULL UNIQUE,
                slug TEXT UNIQUE,
                logo_url TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                moodle_category_id INTEGER,
                moodle_tenant_key TEXT,
                admin_user_id TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS org_feature_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                feature_key TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 0,
                updated_by TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(org_id, feature_key)
            );

            CREATE TABLE IF NOT EXISTS moodle_tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL UNIQUE,
                moodle_cat_id INTEGER NOT NULL,
                sync_status TEXT NOT NULL DEFAULT 'pending',
                last_sync_at TEXT,
                last_error TEXT,
                total_users_lms INTEGER DEFAULT 0,
                total_users_moodle INTEGER DEFAULT 0,
                total_courses INTEGER DEFAULT 0,
                total_enrollments INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS org_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                invited_by TEXT,
                expires_at TEXT NOT NULL,
                accepted_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        # ── Column migrations (safe, idempotent) ────────────────────────────
        # Categories
        _migrate_add_column(conn, "categories", "moodle_category_id", "INTEGER")
        _migrate_add_column(conn, "categories", "org_type", "TEXT NOT NULL DEFAULT 'college'")
        _migrate_add_column(conn, "categories", "organization_id", "INTEGER")
        _migrate_add_column(conn, "categories", "org_id", "INTEGER DEFAULT 1")
        # Users — tenant
        _migrate_add_column(conn, "users", "organization_id", "INTEGER NOT NULL DEFAULT 1")
        _migrate_add_column(conn, "users", "org_id", "INTEGER DEFAULT 1")
        _migrate_add_column(conn, "users", "program", "TEXT")
        _migrate_add_column(conn, "users", "branch", "TEXT")
        _migrate_add_column(conn, "users", "id_number", "TEXT")
        _migrate_add_column(conn, "users", "moodle_id", "INTEGER")
        _migrate_add_column(conn, "users", "is_platform_admin", "INTEGER NOT NULL DEFAULT 0")
        _migrate_add_column(conn, "users", "status", "TEXT DEFAULT 'active'")
        _migrate_add_column(conn, "users", "invited_via", "INTEGER")
        _migrate_add_column(conn, "users", "last_login_at", "TEXT")
        # Pending verifications
        _migrate_add_column(conn, "pending_verifications", "organization_id", "INTEGER NOT NULL DEFAULT 1")
        _migrate_add_column(conn, "pending_verifications", "organization_name", "TEXT NOT NULL DEFAULT 'Unknown'")
        _migrate_add_column(conn, "pending_verifications", "program", "TEXT")
        _migrate_add_column(conn, "pending_verifications", "branch", "TEXT")
        _migrate_add_column(conn, "pending_verifications", "id_number", "TEXT")
        # Courses — tenant
        _migrate_add_column(conn, "courses", "org_id", "INTEGER DEFAULT 1")
        # Enrollment requests — tenant
        _migrate_add_column(conn, "enrollment_requests", "org_id", "INTEGER DEFAULT 1")
        # Tasks — tenant
        _migrate_add_column(conn, "tasks", "org_id", "INTEGER DEFAULT 1")
        # Audit log — enhance
        _migrate_add_column(conn, "audit_log", "org_id", "INTEGER")
        _migrate_add_column(conn, "audit_log", "severity", "TEXT DEFAULT 'INFO'")
        _migrate_add_column(conn, "audit_log", "ip_address", "TEXT")
        _migrate_add_column(conn, "audit_log", "metadata_json", "TEXT")
        # Organizations — enhance existing table
        _migrate_add_column(conn, "organizations", "slug", "TEXT")
        _migrate_add_column(conn, "organizations", "status", "TEXT DEFAULT 'active'")
        _migrate_add_column(conn, "organizations", "logo_url", "TEXT")
        _migrate_add_column(conn, "organizations", "moodle_category_id", "INTEGER")
        _migrate_add_column(conn, "organizations", "moodle_tenant_key", "TEXT")
        _migrate_add_column(conn, "organizations", "created_by", "TEXT")
        _migrate_add_column(conn, "organizations", "updated_at", "TEXT")

        # ── Keep tenant identifiers aligned across legacy/new columns ────────
        _sync_org_context(conn)
        conn.execute("UPDATE tasks SET org_id = COALESCE(org_id, 1)")

        # ── Seed default organizations if none exist ─────────────────────────
        org_count = conn.execute("SELECT COUNT(*) AS count FROM organizations").fetchone()["count"]
        if org_count == 0:
            now = now_local()
            conn.execute(
                "INSERT INTO organizations (id, name, type, domain, slug, status, created_at, updated_at) "
                "VALUES (1, 'Telite University', 'college', 'telite.edu', 'telite-university', 'active', ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO organizations (id, name, type, domain, slug, status, created_at, updated_at) "
                "VALUES (2, 'Telite Systems', 'company', 'telite.io', 'telite-systems', 'active', ?, ?)",
                (now, now),
            )
            conn.commit()
        else:
            # Backfill slug for existing orgs that don't have one
            rows = conn.execute("SELECT id, name FROM organizations WHERE slug IS NULL").fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE organizations SET slug = ?, updated_at = ? WHERE id = ?",
                    (slugify(row["name"]), now_local(), row["id"]),
                )
            if rows:
                conn.commit()

        # ── Seed default feature flags for all orgs ──────────────────────────
        _seed_feature_flags(conn)

        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row["count"] == 0:
            seed_database(conn)

        _sync_org_context(conn)
        _normalize_existing_roles(conn)
        _ensure_global_admin_seed(conn)
        conn.execute("UPDATE tasks SET org_id = COALESCE(org_id, 1)")
        _reset_postgres_sequences(conn)
        conn.commit()


def _reset_postgres_sequence(conn: Any, table: str, column: str = "id") -> None:
    if _connection_backend(conn) != DB_BACKEND_POSTGRES:
        return

    table_name = _safe_identifier(table)
    column_name = _safe_identifier(column)
    row = conn.execute(f"SELECT COALESCE(MAX({column_name}), 0) AS max_id FROM {table_name}").fetchone()
    max_id = int(row["max_id"]) if row and row["max_id"] is not None else 0
    if max_id > 0:
        conn.execute(
            "SELECT setval(pg_get_serial_sequence(?, ?), ?, true)",
            (table_name, column_name, max_id),
        )
        return
    conn.execute(
        "SELECT setval(pg_get_serial_sequence(?, ?), ?, false)",
        (table_name, column_name, 1),
    )


def _reset_postgres_sequences(conn: Any) -> None:
    if _connection_backend(conn) != DB_BACKEND_POSTGRES:
        return
    for table in POSTGRES_SEQUENCE_TABLES:
        _reset_postgres_sequence(conn, table)


def _migrate_add_column(conn: Any, table: str, column: str, col_type: str) -> None:
    """Add a column to an existing table if it doesn't exist (safe migration)."""
    try:
        cols = get_table_columns(conn, table)
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
            logger.info("Migrated: added %s.%s (%s)", table, column, col_type)
    except Exception as exc:
        logger.warning("Migration skipped for %s.%s: %s", table, column, exc)


# ── Feature Flags ────────────────────────────────────────────────────────────

def migrate_sqlite_to_postgres(source_path: str | None = None, *, truncate_existing: bool = True) -> dict[str, Any]:
    if get_db_backend() != DB_BACKEND_POSTGRES:
        raise RuntimeError("Set TELITE_DB_BACKEND=postgres or configure TELITE_DATABASE_URL before migrating.")

    sqlite_path = source_path or os.getenv("TELITE_SQLITE_SOURCE_PATH", "").strip() or get_db_path()
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite source database not found: {sqlite_path}")

    init_db()

    source_conn = sqlite3.connect(sqlite_path)
    source_conn.row_factory = sqlite3.Row
    copied_counts: dict[str, int] = {}

    try:
        source_tables = {
            row["name"]
            for row in source_conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        with get_conn() as target_conn:
            try:
                if truncate_existing:
                    for table in reversed(SQLITE_TO_POSTGRES_TABLE_ORDER):
                        target_conn.execute(f"DELETE FROM {_safe_identifier(table)}")

                for table in SQLITE_TO_POSTGRES_TABLE_ORDER:
                    if table not in source_tables:
                        copied_counts[table] = 0
                        continue

                    source_columns = [
                        row[1]
                        for row in source_conn.execute(f"PRAGMA table_info({_safe_identifier(table)})").fetchall()
                    ]
                    target_columns = set(get_table_columns(target_conn, table))
                    column_names = [name for name in source_columns if name in target_columns]
                    if not column_names:
                        copied_counts[table] = 0
                        continue

                    selected_columns = ", ".join(_safe_identifier(name) for name in column_names)
                    placeholders = ", ".join("?" for _ in column_names)
                    rows = source_conn.execute(
                        f"SELECT {selected_columns} FROM {_safe_identifier(table)}"
                    ).fetchall()
                    if rows:
                        insert_sql = (
                            f"INSERT INTO {_safe_identifier(table)} ({selected_columns}) "
                            f"VALUES ({placeholders})"
                        )
                        payload = [tuple(row[name] for name in column_names) for row in rows]
                        target_conn.executemany(insert_sql, payload)
                    copied_counts[table] = len(rows)

                _sync_org_context(target_conn)
                target_conn.execute("UPDATE tasks SET org_id = COALESCE(org_id, 1)")
                _normalize_existing_roles(target_conn)
                _seed_feature_flags(target_conn)
                _ensure_global_admin_seed(target_conn)
                _reset_postgres_sequences(target_conn)
                target_conn.commit()
            except Exception:
                target_conn.rollback()
                raise
    finally:
        source_conn.close()

    return {
        "backend": get_db_backend(),
        "source_path": sqlite_path,
        "truncate_existing": truncate_existing,
        "rows_copied": copied_counts,
    }


DEFAULT_FEATURE_KEYS = [
    "moodle_access",
    "pal_tracking",
    "analytics",
    "ats_integration",
    "devops_courses",
    "cloud_modules",
]


def _seed_feature_flags(conn: sqlite3.Connection) -> None:
    """Seed default feature flags for all orgs that don't have them yet."""
    org_rows = conn.execute("SELECT id FROM organizations").fetchall()
    for org_row in org_rows:
        org_id = org_row["id"]
        for key in DEFAULT_FEATURE_KEYS:
            existing = conn.execute(
                "SELECT 1 FROM org_feature_flags WHERE org_id = ? AND feature_key = ?",
                (org_id, key),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO org_feature_flags (org_id, feature_key, is_enabled, updated_at) VALUES (?, ?, ?, ?)",
                    (org_id, key, 1 if key in ("moodle_access", "pal_tracking", "analytics") else 0, now_local()),
                )
    conn.commit()


# ── Platform Admin: Organization Queries ──────────────────────────────────────


def list_organizations(
    *,
    org_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List organizations with pagination, filters, and user counts."""
    clauses: list[str] = []
    params: list[Any] = []
    if org_type and org_type != "all":
        clauses.append("o.type = ?")
        params.append(org_type)
    if status and status != "all":
        clauses.append("o.status = ?")
        params.append(status)
    if search:
        clauses.append("(lower(o.name) LIKE ? OR lower(o.domain) LIKE ? OR lower(o.slug) LIKE ?)")
        term = f"%{search.lower()}%"
        params.extend([term, term, term])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM organizations o {where}", params).fetchone()["count"]
        offset = (page - 1) * limit
        rows = conn.execute(
            f"""
            SELECT o.*,
                   (SELECT COUNT(*) FROM users u WHERE u.org_id = o.id AND COALESCE(u.is_platform_admin, 0) = 0) AS user_count
            FROM organizations o
            {where}
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        orgs = []
        for row in rows:
            org = dict(row)
            # Find the super admin for this org
            admin = conn.execute(
                f"SELECT id, full_name, email FROM users WHERE org_id = ? AND role IN ({SQL_TENANT_SUPER_ADMIN_ROLES}) AND COALESCE(is_platform_admin, 0) = 0 LIMIT 1",
                (org["id"],),
            ).fetchone()
            org["super_admin"] = dict(admin) if admin else None
            # Moodle sync status
            mt = conn.execute(
                "SELECT sync_status FROM moodle_tenants WHERE org_id = ?", (org["id"],)
            ).fetchone()
            org["moodle_sync"] = mt["sync_status"] if mt else None
            orgs.append(org)

        return {"orgs": orgs, "total": total, "page": page, "limit": limit}


def get_organization(org_id: int) -> dict[str, Any] | None:
    """Get a single organization with full stats."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not row:
            return None
        org = dict(row)
        org["user_count"] = conn.execute(
            "SELECT COUNT(*) AS count FROM users WHERE org_id = ? AND COALESCE(is_platform_admin, 0) = 0",
            (org_id,),
        ).fetchone()["count"]
        org["users_by_role"] = [
            dict(r) for r in conn.execute(
                "SELECT role, COUNT(*) AS count FROM users WHERE org_id = ? AND COALESCE(is_platform_admin, 0) = 0 GROUP BY role",
                (org_id,),
            ).fetchall()
        ]
        org["course_count"] = conn.execute(
            "SELECT COUNT(*) AS count FROM courses WHERE org_id = ?", (org_id,)
        ).fetchone()["count"]
        # Feature flags
        flags_rows = conn.execute(
            "SELECT feature_key, is_enabled FROM org_feature_flags WHERE org_id = ?", (org_id,)
        ).fetchall()
        org["feature_flags"] = {r["feature_key"]: bool(r["is_enabled"]) for r in flags_rows}
        # Moodle tenant
        mt = conn.execute("SELECT * FROM moodle_tenants WHERE org_id = ?", (org_id,)).fetchone()
        org["moodle_tenant"] = dict(mt) if mt else None
        # Recent audit entries
        org["recent_audit"] = [
            dict(r) for r in conn.execute(
                "SELECT * FROM audit_log WHERE org_id = ? ORDER BY created_at DESC LIMIT 5", (org_id,)
            ).fetchall()
        ]
        # Super admin
        admin = conn.execute(
            f"SELECT id, full_name, email FROM users WHERE org_id = ? AND role IN ({SQL_TENANT_SUPER_ADMIN_ROLES}) AND COALESCE(is_platform_admin, 0) = 0 LIMIT 1",
            (org_id,),
        ).fetchone()
        org["super_admin"] = dict(admin) if admin else None
        return org


def create_organization(payload: dict[str, Any], actor_id: str | None = None) -> dict[str, Any]:
    """Create a new organization."""
    now = now_local()
    with get_conn() as conn:
        # Check uniqueness
        existing = conn.execute("SELECT 1 FROM organizations WHERE domain = ?", (payload["domain"],)).fetchone()
        if existing:
            raise ValueError(f"Domain '{payload['domain']}' is already in use.")
        slug = payload.get("slug") or slugify(payload["name"])
        existing_slug = conn.execute("SELECT 1 FROM organizations WHERE slug = ?", (slug,)).fetchone()
        if existing_slug:
            raise ValueError(f"Slug '{slug}' is already in use.")

        conn.execute(
            """
            INSERT INTO organizations (name, type, domain, slug, status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (payload["name"], payload["type"], payload["domain"], slug, actor_id, now, now),
        )
        conn.commit()
        org_id = conn.execute("SELECT id FROM organizations WHERE slug = ?", (slug,)).fetchone()["id"]
        # Seed feature flags for new org
        for key in DEFAULT_FEATURE_KEYS:
            conn.execute(
                "INSERT INTO org_feature_flags (org_id, feature_key, is_enabled, updated_at) VALUES (?, ?, 0, ?)",
                (org_id, key, now),
            )
        conn.commit()
        return get_organization(org_id) or {}


def update_organization(org_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Update organization fields."""
    allowed_fields = {"name", "domain", "slug", "status", "logo_url", "moodle_category_id", "moodle_tenant_key", "admin_user_id"}
    updates = {k: v for k, v in payload.items() if k in allowed_fields and v is not None}
    if not updates:
        raise ValueError("No valid fields to update.")
    updates["updated_at"] = now_local()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [org_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE organizations SET {set_clause} WHERE id = ?", values)
        conn.commit()
    return get_organization(org_id) or {}


# ── Platform Admin: Feature Flags ─────────────────────────────────────────────


def get_all_org_feature_flags() -> list[dict[str, Any]]:
    """Get feature flags for all orgs."""
    with get_conn() as conn:
        orgs = conn.execute("SELECT id, name, type, status FROM organizations ORDER BY id").fetchall()
        result = []
        for org in orgs:
            flags_rows = conn.execute(
                "SELECT feature_key, is_enabled FROM org_feature_flags WHERE org_id = ?",
                (org["id"],),
            ).fetchall()
            flags = {r["feature_key"]: bool(r["is_enabled"]) for r in flags_rows}
            result.append({
                "org_id": org["id"],
                "org_name": org["name"],
                "org_type": org["type"],
                "org_status": org["status"],
                "flags": flags,
            })
        return result


def toggle_feature_flag(org_id: int, feature_key: str, is_enabled: bool, actor_id: str | None = None) -> dict[str, bool]:
    """Toggle a feature flag for an org."""
    now = now_local()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM org_feature_flags WHERE org_id = ? AND feature_key = ?",
            (org_id, feature_key),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE org_feature_flags SET is_enabled = ?, updated_by = ?, updated_at = ? WHERE org_id = ? AND feature_key = ?",
                (1 if is_enabled else 0, actor_id, now, org_id, feature_key),
            )
        else:
            conn.execute(
                "INSERT INTO org_feature_flags (org_id, feature_key, is_enabled, updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
                (org_id, feature_key, 1 if is_enabled else 0, actor_id, now),
            )
        conn.commit()
        # Return all flags for this org
        rows = conn.execute(
            "SELECT feature_key, is_enabled FROM org_feature_flags WHERE org_id = ?", (org_id,)
        ).fetchall()
        return {r["feature_key"]: bool(r["is_enabled"]) for r in rows}


# ── Platform Admin: Moodle Tenants ────────────────────────────────────────────


def list_moodle_tenants() -> list[dict[str, Any]]:
    """List all moodle tenant records with org info."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT mt.*, o.name AS org_name, o.type AS org_type, o.status AS org_status
            FROM moodle_tenants mt
            JOIN organizations o ON o.id = mt.org_id
            ORDER BY o.name
            """
        ).fetchall()
        return [dict(r) for r in rows]


def upsert_moodle_tenant(org_id: int, moodle_cat_id: int) -> dict[str, Any]:
    """Create or update a moodle tenant record."""
    now = now_local()
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM moodle_tenants WHERE org_id = ?", (org_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE moodle_tenants SET moodle_cat_id = ?, sync_status = 'pending', last_sync_at = NULL WHERE org_id = ?",
                (moodle_cat_id, org_id),
            )
        else:
            conn.execute(
                "INSERT INTO moodle_tenants (org_id, moodle_cat_id, sync_status, created_at) VALUES (?, ?, 'pending', ?)",
                (org_id, moodle_cat_id, now),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM moodle_tenants WHERE org_id = ?", (org_id,)).fetchone()
        return dict(row) if row else {}


def update_moodle_tenant_sync(org_id: int, *, status: str, error: str | None = None, **counts) -> None:
    """Update sync status for a moodle tenant."""
    now = now_local()
    updates = ["sync_status = ?", "last_sync_at = ?"]
    params: list[Any] = [status, now]
    if error is not None:
        updates.append("last_error = ?")
        params.append(error)
    for key in ("total_users_lms", "total_users_moodle", "total_courses", "total_enrollments"):
        if key in counts:
            updates.append(f"{key} = ?")
            params.append(counts[key])
    params.append(org_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE moodle_tenants SET {', '.join(updates)} WHERE org_id = ?", params)
        conn.commit()


# ── Platform Admin: Invitations ───────────────────────────────────────────────


def create_invitation(org_id: int, email: str, role: str, invited_by: str | None = None) -> dict[str, Any]:
    """Create an org invitation."""
    now = now_local()
    token = str(uuid.uuid4())
    normalized_role = normalize_role(role)
    if not is_admin_role(normalized_role):
        raise ValueError("Invitations currently support admin roles only.")
    # expires in 72 hours
    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(hours=72)).strftime("%Y-%m-%d %H:%M")
    with get_conn() as conn:
        # Check for existing pending invitation
        existing = conn.execute(
            "SELECT id FROM org_invitations WHERE email = ? AND org_id = ? AND accepted_at IS NULL AND expires_at > ?",
            (email, org_id, now),
        ).fetchone()
        if existing:
            raise ValueError(f"An active invitation for {email} already exists for this organization.")
        conn.execute(
            "INSERT INTO org_invitations (org_id, email, role, token, invited_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (org_id, email, normalized_role, token, invited_by, expires_at, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM org_invitations WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else {}


def validate_invitation(token: str) -> dict[str, Any] | None:
    """Validate an invitation token. Returns invitation data or None."""
    now = now_local()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT inv.*, o.name AS org_name, o.type AS org_type FROM org_invitations inv JOIN organizations o ON o.id = inv.org_id WHERE inv.token = ? AND inv.accepted_at IS NULL AND inv.expires_at > ?",
            (token, now),
        ).fetchone()
        return dict(row) if row else None


def accept_invitation(token: str) -> dict[str, Any]:
    """Mark an invitation as accepted."""
    now = now_local()
    with get_conn() as conn:
        conn.execute(
            "UPDATE org_invitations SET accepted_at = ? WHERE token = ?", (now, token)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM org_invitations WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else {}


def accept_invitation_signup(token: str, full_name: str, password: str) -> dict[str, Any]:
    now = now_local()
    with get_conn() as conn:
        invitation = conn.execute(
            """
            SELECT inv.*, o.name AS org_name, o.type AS org_type
            FROM org_invitations inv
            JOIN organizations o ON o.id = inv.org_id
            WHERE inv.token = ? AND inv.accepted_at IS NULL AND inv.expires_at > ?
            LIMIT 1
            """,
            (token, now),
        ).fetchone()
        if not invitation:
            raise ValueError("Invitation not found or expired.")

        invitation_data = dict(invitation)
        user = _create_user_record(
            conn,
            email=invitation_data["email"],
            full_name=full_name.strip(),
            role=invitation_data["role"],
            password_hash_value=hash_password(password),
            org_id=invitation_data["org_id"],
            invited_via=invitation_data["id"],
        )
        conn.execute(
            "UPDATE org_invitations SET accepted_at = ? WHERE id = ?",
            (now, invitation_data["id"]),
        )
        _insert_audit(
            conn,
            actor_id=user["id"],
            actor_name=user["full_name"],
            action="invitation.accept",
            target_type="invitation",
            target_id=str(invitation_data["id"]),
            message=f"{user['full_name']} accepted an invitation for {invitation_data['org_name']}",
            accent="emerald",
            result="accepted",
            org_id=invitation_data["org_id"],
        )
        conn.commit()
        return user


def create_password_reset_token(email: str) -> dict[str, Any] | None:
    normalized_email = email.strip().lower()
    if not normalized_email:
        return None
    now = now_local()
    expires_at = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM users
            WHERE lower(email) = lower(?) AND is_active = 1
            LIMIT 1
            """,
            (normalized_email,),
        ).fetchone()
        if not row:
            return None
        user = serialize_user(row, include_secret=True)
        if not user:
            return None
        conn.execute(
            """
            UPDATE password_reset_tokens
            SET used_at = ?
            WHERE user_id = ? AND used_at IS NULL
            """,
            (now, user["id"]),
        )
        token = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, expires_at, used_at, created_at)
            VALUES (?, ?, ?, NULL, ?)
            """,
            (user["id"], token, expires_at, now),
        )
        conn.commit()
        return {
            "user_id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "token": token,
            "expires_at": expires_at,
            "org_id": user.get("org_id"),
        }


def validate_password_reset_token(token: str) -> dict[str, Any] | None:
    now = now_local()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT prt.*, u.email, u.full_name, u.org_id, u.organization_id
            FROM password_reset_tokens prt
            JOIN users u ON u.id = prt.user_id
            WHERE prt.token = ? AND prt.used_at IS NULL AND prt.expires_at > ? AND u.is_active = 1
            LIMIT 1
            """,
            (token, now),
        ).fetchone()
        return dict(row) if row else None


def reset_password_with_token(token: str, new_password: str) -> dict[str, Any]:
    reset_token = validate_password_reset_token(token)
    if not reset_token:
        raise ValueError("Reset token is invalid or expired.")
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), reset_token["user_id"]),
        )
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE token = ?",
            (now_local(), token),
        )
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (now_local(), reset_token["user_id"]),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (reset_token["user_id"],)).fetchone()
        user = serialize_user(row, include_secret=True)
        if not user:
            raise ValueError("User not found.")
        return user


def list_pending_invitations(org_id: int | None = None) -> list[dict[str, Any]]:
    """List pending (unaccepted, unexpired) invitations."""
    now = now_local()
    with get_conn() as conn:
        if org_id is not None:
            rows = conn.execute(
                "SELECT inv.*, o.name AS org_name FROM org_invitations inv JOIN organizations o ON o.id = inv.org_id WHERE inv.org_id = ? AND inv.accepted_at IS NULL AND inv.expires_at > ? ORDER BY inv.created_at DESC",
                (org_id, now),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT inv.*, o.name AS org_name FROM org_invitations inv JOIN organizations o ON o.id = inv.org_id WHERE inv.accepted_at IS NULL AND inv.expires_at > ? ORDER BY inv.created_at DESC",
                (now,),
            ).fetchall()
        return [dict(r) for r in rows]


# ── Platform Admin: Enhanced Audit Log ────────────────────────────────────────


def write_platform_audit(
    *,
    action: str,
    actor_id: str | None = None,
    actor_name: str = "System",
    org_id: int | None = None,
    target_type: str = "",
    target_id: str = "",
    message: str = "",
    severity: str = "INFO",
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an enhanced audit log entry."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (actor_user_id, actor_name, action, target_type, target_id, message, accent, result, created_at, org_id, severity, ip_address, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor_id, actor_name, action, target_type, target_id, message,
                "blue",  # accent
                "ok",    # result
                now_local(), org_id, severity, ip_address,
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()


def list_audit_logs(
    *,
    org_id: int | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """List audit logs with filters and pagination."""
    clauses: list[str] = []
    params: list[Any] = []
    if org_id is not None:
        clauses.append("org_id = ?")
        params.append(org_id)
    if actor_id:
        clauses.append("actor_user_id = ?")
        params.append(actor_id)
    if action:
        clauses.append("lower(action) LIKE ?")
        params.append(f"%{action.lower()}%")
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if from_date:
        clauses.append("created_at >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("created_at <= ?")
        params.append(to_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM audit_log {where}", params).fetchone()["count"]
        offset = (page - 1) * limit
        rows = conn.execute(
            f"SELECT * FROM audit_log {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return {"logs": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}


# ── Platform Admin: Analytics ─────────────────────────────────────────────────


def platform_analytics_overview() -> dict[str, Any]:
    """Global analytics for the platform admin dashboard."""
    with get_conn() as conn:
        total_orgs = conn.execute("SELECT COUNT(*) AS c FROM organizations").fetchone()["c"]
        total_colleges = conn.execute("SELECT COUNT(*) AS c FROM organizations WHERE type = 'college'").fetchone()["c"]
        total_companies = conn.execute("SELECT COUNT(*) AS c FROM organizations WHERE type = 'company'").fetchone()["c"]
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_platform_admin = 0").fetchone()["c"]
        total_super_admins = conn.execute(
            f"SELECT COUNT(*) AS c FROM users WHERE role IN ({SQL_TENANT_SUPER_ADMIN_ROLES}) AND COALESCE(is_platform_admin, 0) = 0"
        ).fetchone()["c"]

        # Users per org
        org_usage = [
            dict(r) for r in conn.execute(
                """
                SELECT o.id AS org_id, o.name AS org_name, o.type AS org_type,
                       (SELECT COUNT(*) FROM users u WHERE u.org_id = o.id AND COALESCE(u.is_platform_admin, 0) = 0) AS user_count
                FROM organizations o
                ORDER BY user_count DESC
                """
            ).fetchall()
        ]

        # Moodle health
        mt_rows = conn.execute(
            "SELECT sync_status, COUNT(*) AS c FROM moodle_tenants GROUP BY sync_status"
        ).fetchall()
        moodle_health = {"synced": 0, "failed": 0, "pending": 0}
        for r in mt_rows:
            if r["sync_status"] in moodle_health:
                moodle_health[r["sync_status"]] = r["c"]

        # Recent activity
        recent_activity = [
            dict(r) for r in conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 8"
            ).fetchall()
        ]

        return {
            "total_orgs": total_orgs,
            "total_colleges": total_colleges,
            "total_companies": total_companies,
            "total_users": total_users,
            "total_super_admins": total_super_admins,
            "org_usage": org_usage,
            "moodle_health": moodle_health,
            "recent_activity": recent_activity,
        }


def seed_database(conn: sqlite3.Connection) -> None:
    payload = build_seed_payload()
    created_at = now_local()

    _exec_many(
        conn,
        """
        INSERT INTO users (
            id, username, email, full_name, role, category_scope, password_hash,
            avatar_initials, gradient_start, gradient_end, is_active, pal_score,
            pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
            pal_task_completion_pct, streak_days, courses_completed, total_courses,
            cohort_rank, enrollment_type, current_course_id, course_progress_json,
            created_at, last_login
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                user["id"],
                user["username"],
                user["email"],
                user["full_name"],
                user["role"],
                user["category_scope"],
                hash_password(user["password"]),
                user["avatar_initials"],
                user["gradient_start"],
                user["gradient_end"],
                1,
                user["pal_score"],
                user["pal_completion_pct"],
                user["pal_quiz_avg"],
                user["pal_time_spent_hours"],
                user["pal_task_completion_pct"],
                user["streak_days"],
                user["courses_completed"],
                user["total_courses"],
                user["cohort_rank"],
                user["enrollment_type"],
                user["current_course_id"],
                json.dumps(user["course_progress"]),
                created_at,
                None,
            )
            for user in payload["users"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO categories (
            id, name, slug, description, status, accent_color, admin_user_id,
            planned_courses, avg_pal_target, created_at, archived_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                category["id"],
                category["name"],
                category["slug"],
                category["description"],
                category["status"],
                category["accent_color"],
                category["admin_user_id"],
                category["planned_courses"],
                category["avg_pal_target"],
                created_at,
                None,
            )
            for category in payload["categories"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO courses (
            id, moodle_course_id, category_slug, name, slug, description, tier, status,
            module_count, modules_json, lessons_count, hours, enrolled_count,
            completion_rate, completion_count, avg_quiz_score, prerequisite_course_id, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                course["id"],
                course["moodle_course_id"],
                course["category_slug"],
                course["name"],
                course["slug"],
                course["description"],
                course["tier"],
                course["status"],
                course["module_count"],
                json.dumps(course["modules"]),
                course["lessons_count"],
                course["hours"],
                course["enrolled_count"],
                course["completion_rate"],
                course["completion_count"],
                course["avg_quiz_score"],
                course["prerequisite_course_id"],
                created_at,
            )
            for course in payload["courses"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO enrollment_requests (
            id, full_name, email, category_slug, request_type, company_domain,
            domain_verified, status, requested_at, reviewed_by, reviewed_at, rejection_reason
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                request["id"],
                request["full_name"],
                request["email"],
                request["category_slug"],
                request["request_type"],
                request["company_domain"],
                int(request["domain_verified"]),
                request["status"],
                request["requested_at"],
                request["reviewed_by"],
                request["reviewed_at"],
                request["rejection_reason"],
            )
            for request in payload["enrollment_requests"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO tasks (
            id, title, description, assigned_label, assigned_to_user_id, assignment_scope,
            category_slug, due_at, status, created_at, assigned_by, notes, is_cross_category
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                task["id"],
                task["title"],
                task["description"],
                task["assigned_label"],
                task["assigned_to_user_id"],
                task["assignment_scope"],
                task["category_slug"],
                task["due_at"],
                task["status"],
                created_at,
                task["assigned_by"],
                task["notes"],
                task["is_cross_category"],
            )
            for task in payload["tasks"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO audit_log (
            actor_user_id, actor_name, action, target_type, target_id, message, accent, result, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                entry["actor_user_id"],
                entry["actor_name"],
                entry["action"],
                entry["target_type"],
                entry["target_id"],
                entry["message"],
                entry["accent"],
                entry["result"],
                entry["created_at"],
            )
            for entry in payload["audit_log"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO activity_log (
            user_id, category_slug, icon, accent, message, created_at
        ) VALUES (?,?,?,?,?,?)
        """,
        [
            (
                entry["user_id"],
                entry["category_slug"],
                entry["icon"],
                entry["accent"],
                entry["message"],
                entry["created_at"],
            )
            for entry in payload["activity_log"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO notifications (
            user_id, title, body, is_read, created_at
        ) VALUES (?,?,?,?,?)
        """,
        [
            (
                note["user_id"],
                note["title"],
                note["body"],
                note["is_read"],
                note["created_at"],
            )
            for note in payload["notifications"]
        ],
    )

    _exec_many(
        conn,
        """
        INSERT INTO allowed_domains (
            domain, label, added_by, created_at
        ) VALUES (?,?,?,?)
        """,
        [
            (
                row["domain"],
                row["label"],
                row["added_by"],
                created_at,
            )
            for row in payload["allowed_domains"]
        ],
    )
    conn.commit()


def fetch_user_by_identifier(identifier: str, *, include_secret: bool = False) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM users
            WHERE lower(username) = lower(?) OR lower(email) = lower(?)
            LIMIT 1
            """,
            (identifier, identifier),
        ).fetchone()
        return serialize_user(row, include_secret=include_secret) if row else None


def fetch_user_by_id(user_id: str, *, include_secret: bool = False) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return serialize_user(row, include_secret=include_secret) if row else None


def serialize_user(row: sqlite3.Row | None, *, include_secret: bool = False) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["course_progress"] = _json_load(item.pop("course_progress_json", "[]"), [])
    item["is_active"] = bool(item["is_active"])
    item["avatar_gradient"] = [item.pop("gradient_start"), item.pop("gradient_end")]
    if not include_secret:
        item.pop("password_hash", None)
    return item


def _build_unique_username(
    conn: sqlite3.Connection,
    *,
    full_name: str,
    email: str | None = None,
) -> str:
    candidates: list[str] = []
    if email:
        local_part = slugify(email.split("@", 1)[0]).replace("-", ".")
        if local_part:
            candidates.append(local_part)
    name_candidate = slugify(full_name).replace("-", ".")
    if name_candidate:
        candidates.append(name_candidate)
    if not candidates:
        candidates.append(f"user.{uuid.uuid4().hex[:8]}")

    for candidate in candidates:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE lower(username) = lower(?)",
            (candidate,),
        ).fetchone()
        if not existing:
            return candidate

    base = candidates[-1]
    while True:
        candidate = f"{base}.{uuid.uuid4().hex[:4]}"
        existing = conn.execute(
            "SELECT 1 FROM users WHERE lower(username) = lower(?)",
            (candidate,),
        ).fetchone()
        if not existing:
            return candidate


def _create_user_record(
    conn: sqlite3.Connection,
    *,
    email: str,
    full_name: str,
    role: str,
    password_hash_value: str,
    org_id: int,
    category_scope: str | None = None,
    username: str | None = None,
    invited_via: int | None = None,
    is_active: bool = True,
    status: str = "active",
    program: str | None = None,
    branch: str | None = None,
    id_number: str | None = None,
    enrollment_type: str | None = None,
    current_course_id: str | None = None,
    total_courses: int = 0,
    course_progress: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    normalized_role = normalize_role(role)
    if conn.execute(
        "SELECT 1 FROM users WHERE lower(email) = lower(?)",
        (normalized_email,),
    ).fetchone():
        raise ValueError("An account with this email already exists.")

    final_username = (username or "").strip().lower() or _build_unique_username(
        conn,
        full_name=full_name,
        email=normalized_email,
    )
    if conn.execute(
        "SELECT 1 FROM users WHERE lower(username) = lower(?)",
        (final_username,),
    ).fetchone():
        raise ValueError("A user with this username already exists.")

    if not is_admin_role(normalized_role):
        category_scope = category_scope or None

    user_id = f"user-{slugify(full_name)}-{uuid.uuid4().hex[:6]}"
    gradient_start, gradient_end = role_gradients(normalized_role)
    conn.execute(
        """
        INSERT INTO users (
            id, username, email, full_name, role, category_scope, password_hash,
            avatar_initials, gradient_start, gradient_end, is_active, pal_score,
            pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
            pal_task_completion_pct, streak_days, courses_completed, total_courses,
            cohort_rank, enrollment_type, current_course_id, course_progress_json,
            created_at, last_login, organization_id, org_id, program, branch, id_number,
            invited_via, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            final_username,
            normalized_email,
            full_name,
            normalized_role,
            category_scope,
            password_hash_value,
            initials(full_name),
            gradient_start,
            gradient_end,
            int(is_active),
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            total_courses,
            None,
            enrollment_type,
            current_course_id,
            json.dumps(course_progress or []),
            now_local(),
            None,
            org_id,
            org_id,
            program,
            branch,
            id_number,
            invited_via,
            status,
        ),
    )
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    user = serialize_user(row, include_secret=True)
    if not user:
        raise ValueError("Failed to create user.")
    return user


def serialize_course(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["modules"] = _json_load(item.pop("modules_json", "[]"), [])
    return item


def list_categories(*, include_archived: bool = True, org_id: int | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        clauses = []
        params: list[Any] = []
        if not include_archived:
            clauses.append("c.status != 'archived'")
        if org_id is not None:
            clauses.append("COALESCE(c.org_id, c.organization_id) = ?")
            params.append(org_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                c.*,
                u.full_name AS admin_name,
                u.email AS admin_email,
                (
                    SELECT COUNT(*) FROM courses course
                    WHERE course.category_slug = c.slug AND course.status != 'archived'
                ) AS total_courses,
                (
                    SELECT COUNT(*) FROM users learner
                    WHERE learner.role IN ({SQL_LEARNER_ROLES})
                      AND learner.category_scope = c.slug
                      AND learner.is_active = 1
                ) AS total_learners
            FROM categories c
            LEFT JOIN users u ON u.id = c.admin_user_id
            {where}
            ORDER BY CASE c.slug WHEN 'ats' THEN 1 WHEN 'devops' THEN 2 ELSE 3 END, c.name
            """,
            params,
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["avg_pal"] = item.pop("avg_pal_target")
            result.append(item)
        return result


def get_category(category_slug: str, org_id: int | None = None) -> dict[str, Any] | None:
    with get_conn() as conn:
        clauses = ["(id = ? OR slug = ?)"]
        params: list[Any] = [category_slug, category_slug]
        if org_id is not None:
            clauses.append("COALESCE(org_id, organization_id) = ?")
            params.append(org_id)
        row = conn.execute(
            f"SELECT * FROM categories WHERE {' AND '.join(clauses)} LIMIT 1",
            params,
        ).fetchone()
        return dict(row) if row else None


def list_courses(
    category_slug: str | None = None,
    *,
    include_archived: bool = True,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    with get_conn() as conn:
        clauses = []
        params: list[Any] = []
        if category_slug:
            clauses.append("category_slug = ?")
            params.append(category_slug)
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        if not include_archived:
            clauses.append("status != 'archived'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM courses {where} ORDER BY category_slug, moodle_course_id, name",
            params,
        ).fetchall()
        return [serialize_course(row) for row in rows if row]


def get_course(course_id: str, org_id: int | None = None) -> dict[str, Any] | None:
    with get_conn() as conn:
        clauses = ["(id = ? OR slug = ?)"]
        params: list[Any] = [course_id, course_id]
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        row = conn.execute(
            f"SELECT * FROM courses WHERE {' AND '.join(clauses)} LIMIT 1",
            params,
        ).fetchone()
        return serialize_course(row) if row else None


def list_admins(org_id: int | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        clauses = [f"role IN ({SQL_ADMIN_ROLES})", "is_active = 1", "COALESCE(is_platform_admin, 0) = 0"]
        params: list[Any] = []
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        rows = conn.execute(
            f"""
            SELECT * FROM users
            WHERE {' AND '.join(clauses)}
            ORDER BY full_name
            """,
            params,
        ).fetchall()
        admins = [serialize_user(row) for row in rows if row]
        return sorted((admin for admin in admins if admin), key=lambda admin: (role_priority(admin["role"]), admin["full_name"]))


def list_users(
    *,
    role: str | None = None,
    category_slug: str | None = None,
    query: str | None = None,
    enrollment_type: str | None = None,
    org_id: int | None = None,
    include_inactive: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    clauses = ["COALESCE(is_platform_admin, 0) = 0"]
    params: list[Any] = []
    if role:
        role_values = expand_role_filter(role)
        placeholders = ",".join("?" for _ in role_values)
        clauses.append(f"role IN ({placeholders})")
        params.extend(role_values)
    if category_slug:
        clauses.append("category_scope = ?")
        params.append(category_slug)
    if query:
        clauses.append("(lower(full_name) LIKE ? OR lower(email) LIKE ?)")
        q = f"%{query.lower()}%"
        params.extend([q, q])
    if enrollment_type:
        clauses.append("enrollment_type = ?")
        params.append(enrollment_type)
    if org_id is not None:
        clauses.append("org_id = ?")
        params.append(org_id)
    if not include_inactive:
        clauses.append("is_active = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM users {where}", params).fetchone()["count"]
        query_sql = f"""
            SELECT * FROM users
            {where}
            ORDER BY full_name
        """
        if limit is not None:
            query_sql += " LIMIT ? OFFSET ?"
            params = params + [limit, offset]
        rows = conn.execute(query_sql, params).fetchall()
        users = [serialize_user(row) for row in rows if row]
        users = sorted((user for user in users if user), key=lambda user: (role_priority(user["role"]), user["full_name"]))
        return {
            "total": total,
            "users": users,
        }


def list_notifications(user_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_audit_entries(*, limit: int = 10, org_id: int | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        clauses: list[str] = []
        params: list[Any] = []
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT * FROM audit_log
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
        return [dict(row) for row in rows]


def list_activity_entries(
    *,
    category_slug: str | None = None,
    user_id: str | None = None,
    limit: int = 10,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if category_slug:
        clauses.append("category_slug = ?")
        params.append(category_slug)
    if user_id:
        clauses.append("(user_id = ? OR user_id IS NULL)")
        params.append(user_id)
    if org_id is not None:
        clauses.append(
            """
            (
                (user_id IS NOT NULL AND user_id IN (SELECT id FROM users WHERE org_id = ?))
                OR (category_slug IS NOT NULL AND category_slug IN (SELECT slug FROM categories WHERE COALESCE(org_id, organization_id) = ?))
            )
            """
        )
        params.extend([org_id, org_id])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM activity_log
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
        return [dict(row) for row in rows]


def list_enrollment_requests(
    *,
    category_slug: str | None = None,
    statuses: list[str] | None = None,
    limit: int | None = None,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if category_slug:
        clauses.append("category_slug = ?")
        params.append(category_slug)
    if org_id is not None:
        clauses.append("org_id = ?")
        params.append(org_id)
    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        clauses.append(f"status IN ({placeholders})")
        params.extend(statuses)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM enrollment_requests
        {where}
        ORDER BY requested_at DESC
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["domain_verified"] = bool(item["domain_verified"])
            result.append(item)
        return result


def list_tasks(
    *,
    category_slug: str | None = None,
    viewer: dict[str, Any] | None = None,
    include_cross_category: bool = True,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    effective_org_id = org_id if org_id is not None else _extract_org_id(viewer)
    if category_slug:
        clauses.append("(category_slug = ? OR category_slug = 'all')")
        params.append(category_slug)
    if effective_org_id is not None:
        clauses.append("org_id = ?")
        params.append(effective_org_id)
    if not include_cross_category:
        clauses.append("is_cross_category = 0")
    if viewer and is_learner_role(viewer["role"]):
        clauses.append(
            """
            (
                assigned_to_user_id = ?
                OR (assignment_scope = 'all_learners' AND (category_slug = ? OR category_slug = 'all'))
                OR (assignment_scope = 'all_categories')
            )
            """
        )
        params.extend([viewer["id"], viewer["category_scope"]])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM tasks
            {where}
            ORDER BY
                CASE status
                    WHEN 'overdue' THEN 0
                    WHEN 'pending' THEN 1
                    WHEN 'in_progress' THEN 2
                    ELSE 3
                END,
                due_at
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def count_pending_approvals(org_id: int | None = None) -> int:
    with get_conn() as conn:
        clauses = ["status IN ('pending', 'flagged')"]
        params: list[Any] = []
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM enrollment_requests
            WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchone()
        return row["count"]


def count_active_learners(org_id: int | None = None) -> int:
    with get_conn() as conn:
        clauses = [f"role IN ({SQL_LEARNER_ROLES})", "is_active = 1"]
        params: list[Any] = []
        if org_id is not None:
            clauses.append("org_id = ?")
            params.append(org_id)
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM users
            WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchone()
        return row["count"]


def create_session(user_id: str, refresh_token: str, expires_at: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (id, user_id, refresh_token, expires_at, revoked_at, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (str(uuid.uuid4()), user_id, refresh_token, expires_at, None, now_local()),
        )
        conn.commit()


def get_session_by_token(refresh_token: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM auth_sessions
            WHERE refresh_token = ? AND revoked_at IS NULL
            LIMIT 1
            """,
            (refresh_token,),
        ).fetchone()
        return dict(row) if row else None


def revoke_session(refresh_token: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE refresh_token = ?",
            (now_local(), refresh_token),
        )
        conn.commit()


def update_last_login(user_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = ?, last_login_at = ? WHERE id = ?",
            (now_local(), now_local(), user_id),
        )
        conn.commit()


def _insert_audit(
    conn: sqlite3.Connection,
    *,
    actor_id: str | None,
    actor_name: str,
    action: str,
    target_type: str,
    target_id: str,
    message: str,
    accent: str,
    result: str,
    org_id: int | None = None,
) -> None:
    resolved_org_id = org_id
    if resolved_org_id is None and actor_id:
        actor_row = conn.execute(
            "SELECT org_id, organization_id FROM users WHERE id = ?",
            (actor_id,),
        ).fetchone()
        resolved_org_id = _extract_org_id(actor_row)
    conn.execute(
        """
        INSERT INTO audit_log (
            actor_user_id, actor_name, action, target_type, target_id, message, accent, result, created_at, org_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (actor_id, actor_name, action, target_type, target_id, message, accent, result, now_local(), resolved_org_id),
    )


def _insert_activity(
    conn: sqlite3.Connection,
    *,
    user_id: str | None,
    category_slug: str | None,
    icon: str,
    accent: str,
    message: str,
) -> None:
    conn.execute(
        """
        INSERT INTO activity_log (user_id, category_slug, icon, accent, message, created_at)
        VALUES (?,?,?,?,?,?)
        """,
        (user_id, category_slug, icon, accent, message, now_local()),
    )


def _insert_notification(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    title: str,
    body: str,
) -> None:
    conn.execute(
        """
        INSERT INTO notifications (user_id, title, body, is_read, created_at)
        VALUES (?,?,?,?,?)
        """,
        (user_id, title, body, 0, now_local()),
    )


def ensure_category_access(user: dict[str, Any], category_slug: str) -> None:
    with get_conn() as conn:
        category_org_id = _lookup_category_org_id(conn, category_slug)
    user_org_id = _extract_org_id(user)
    if user.get("is_platform_admin"):
        return
    if category_org_id is not None and user_org_id is not None and category_org_id != user_org_id:
        raise PermissionError("You do not have access to this organization.")
    if is_tenant_super_admin_role(user["role"]):
        return
    if is_category_admin_role(user["role"]) and user["category_scope"] == category_slug:
        return
    raise PermissionError("You do not have access to this category.")


def create_category(payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
    category_id = f"cat-{slugify(payload['slug'])}"
    category_org_id = payload.get("org_id") or payload.get("organization_id") or _extract_org_id(actor) or 1
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM categories WHERE slug = ?",
            (payload["slug"],),
        ).fetchone()
        if existing:
            raise ValueError("Category slug already exists.")

        conn.execute(
            """
            INSERT INTO categories (
                id, name, slug, description, status, accent_color, admin_user_id,
                planned_courses, avg_pal_target, moodle_category_id, org_type,
                organization_id, org_id, created_at, archived_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                category_id,
                payload["name"],
                payload["slug"],
                payload.get("description", ""),
                payload.get("status", "active").lower(),
                payload.get("accent_color", "#7C3AED"),
                payload.get("admin_user_id"),
                int(payload.get("planned_courses", 0)),
                0,
                payload.get("moodle_category_id"),
                payload.get("org_type", "college"),
                category_org_id,
                category_org_id,
                now_local(),
                None,
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="category.create",
            target_type="category",
            target_id=category_id,
            message=f"{actor['full_name']} created category {payload['name']}",
            accent="emerald",
            result="success",
            org_id=category_org_id,
        )
        conn.commit()
    return get_category(payload["slug"], org_id=category_org_id)


def update_category_moodle_id(category_id: str, moodle_category_id: int) -> None:
    """Store the Moodle-assigned category ID in the local DB after successful sync."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE categories SET moodle_category_id = ? WHERE id = ?",
            (moodle_category_id, category_id),
        )
        conn.commit()
        logger.info("Stored moodle_category_id=%d for category=%s", moodle_category_id, category_id)


def update_category(category_id: str, payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM categories WHERE id = ? OR slug = ? LIMIT 1",
            (category_id, category_id),
        ).fetchone()
        if not row:
            raise ValueError("Category not found.")
        category = dict(row)
        next_slug = payload.get("slug", category["slug"])
        if next_slug != category["slug"]:
            duplicate = conn.execute(
                "SELECT 1 FROM categories WHERE slug = ? AND id != ?",
                (next_slug, category["id"]),
            ).fetchone()
            if duplicate:
                raise ValueError("Category slug already exists.")

        conn.execute(
            """
            UPDATE categories
            SET name = ?, slug = ?, description = ?, status = ?, admin_user_id = ?, planned_courses = ?
            WHERE id = ?
            """,
            (
                payload.get("name", category["name"]),
                next_slug,
                payload.get("description", category["description"]),
                payload.get("status", category["status"]).lower(),
                payload.get("admin_user_id", category["admin_user_id"]),
                int(payload.get("planned_courses", category["planned_courses"])),
                category["id"],
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="category.update",
            target_type="category",
            target_id=category["id"],
            message=f"{actor['full_name']} updated category {payload.get('name', category['name'])}",
            accent="violet",
            result="success",
        )
        conn.commit()
        return get_category(next_slug) or {}


def archive_category(category_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM categories WHERE id = ? OR slug = ? LIMIT 1",
            (category_id, category_id),
        ).fetchone()
        if not row:
            raise ValueError("Category not found.")
        category = dict(row)
        conn.execute(
            "UPDATE categories SET status = 'archived', archived_at = ? WHERE id = ?",
            (now_local(), category["id"]),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="category.archive",
            target_type="category",
            target_id=category["id"],
            message=f"{actor['full_name']} archived category {category['name']}",
            accent="red",
            result="archived",
        )
        conn.commit()
        return get_category(category["slug"]) or {}


def create_or_update_admin(payload: dict[str, Any], actor: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    email = payload["email"].strip().lower()
    if not email.endswith("@telite.io"):
        raise ValueError("Admin email must use the @telite.io domain.")
    role = normalize_role(payload["role"])
    if not is_admin_role(role):
        raise ValueError("This endpoint only supports admin-level roles.")

    with get_conn() as conn:
        admin_org_id = (
            _lookup_category_org_id(conn, payload.get("category_scope"))
            or payload.get("org_id")
            or payload.get("organization_id")
            or _extract_org_id(actor)
            or 1
        )
        if user_id:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                raise ValueError("Admin not found.")
            existing = dict(row)
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, email = ?, role = ?, category_scope = ?, is_active = 1,
                    organization_id = ?, org_id = ?
                WHERE id = ?
                """,
                (
                    payload["full_name"],
                    email,
                    role,
                    payload.get("category_scope"),
                    admin_org_id,
                    admin_org_id,
                    user_id,
                ),
            )
            _insert_audit(
                conn,
                actor_id=actor["id"],
                actor_name=actor["full_name"],
                action="admin.update",
                target_type="user",
                target_id=user_id,
                message=f"{actor['full_name']} updated admin {payload['full_name']}",
                accent="violet",
                result="success",
                org_id=admin_org_id,
            )
            conn.commit()
            return fetch_user_by_id(user_id) or existing

        user_id = f"user-{slugify(payload['full_name'])}"
        duplicate = conn.execute(
            "SELECT 1 FROM users WHERE email = ? OR username = ?",
            (email, payload.get("username", slugify(payload["full_name"]))),
        ).fetchone()
        if duplicate:
            raise ValueError("A user with this email already exists.")

        username = payload.get("username") or slugify(payload["full_name"]).replace("-", ".")
        category_scope = payload.get("category_scope")
        gradient_start, gradient_end = role_gradients(role)
        conn.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, role, category_scope, password_hash,
                avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                pal_task_completion_pct, streak_days, courses_completed, total_courses,
                cohort_rank, enrollment_type, current_course_id, course_progress_json, created_at,
                last_login, organization_id, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                username,
                email,
                payload["full_name"],
                role,
                category_scope,
                hash_password(payload.get("password", "Admin@1234")),
                initials(payload["full_name"]),
                gradient_start,
                gradient_end,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                None,
                "[]",
                now_local(),
                None,
                admin_org_id,
                admin_org_id,
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="admin.create",
            target_type="user",
            target_id=user_id,
            message=f"{actor['full_name']} added admin {payload['full_name']}",
            accent="violet",
            result="success",
            org_id=admin_org_id,
        )
        conn.commit()
        return fetch_user_by_id(user_id) or {}


def remove_admin(user_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT * FROM users WHERE id = ? AND role IN ({SQL_ADMIN_ROLES})",
            (user_id,),
        ).fetchone()
        if not row:
            raise ValueError("Admin not found.")
        admin = dict(row)
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="admin.remove",
            target_type="user",
            target_id=user_id,
            message=f"{actor['full_name']} removed admin {admin['full_name']}",
            accent="red",
            result="archived",
        )
        conn.commit()
        return fetch_user_by_id(user_id) or serialize_user(row)


def create_or_update_course(
    category_slug: str,
    payload: dict[str, Any],
    actor: dict[str, Any],
    course_id: str | None = None,
) -> dict[str, Any]:
    with get_conn() as conn:
        course_org_id = _lookup_category_org_id(conn, category_slug) or _extract_org_id(actor) or 1
        if course_id:
            row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
            if not row:
                raise ValueError("Course not found.")
            course = dict(row)
            next_slug = payload.get("slug", course["slug"])
            conn.execute(
                """
                UPDATE courses
                SET name = ?, slug = ?, description = ?, tier = ?, status = ?, module_count = ?,
                    modules_json = ?, lessons_count = ?, hours = ?, prerequisite_course_id = ?
                WHERE id = ?
                """,
                (
                    payload.get("name", course["name"]),
                    next_slug,
                    payload.get("description", course["description"]),
                    payload.get("tier", course["tier"]),
                    payload.get("status", course["status"]),
                    int(payload.get("module_count", course["module_count"])),
                    json.dumps(payload.get("modules", _json_load(course["modules_json"], []))),
                    int(payload.get("lessons_count", course["lessons_count"])),
                    float(payload.get("hours", course["hours"])),
                    payload.get("prerequisite_course_id", course["prerequisite_course_id"]),
                    course_id,
                ),
            )
            _insert_audit(
                conn,
                actor_id=actor["id"],
                actor_name=actor["full_name"],
                action="course.update",
                target_type="course",
                target_id=course_id,
                message=f"{actor['full_name']} updated course {payload.get('name', course['name'])}",
                accent="brand",
                result="success",
                org_id=course_org_id,
            )
            conn.commit()
            return get_course(course_id, org_id=course_org_id) or {}

        new_id = f"course-{slugify(payload.get('slug') or payload['name'])}"
        conn.execute(
            """
            INSERT INTO courses (
                id, moodle_course_id, category_slug, name, slug, description, tier, status,
                module_count, modules_json, lessons_count, hours, enrolled_count,
                completion_rate, completion_count, avg_quiz_score, prerequisite_course_id, created_at, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id,
                payload.get("moodle_course_id"),
                category_slug,
                payload["name"],
                payload.get("slug") or slugify(payload["name"]),
                payload["description"],
                payload["tier"],
                payload.get("status", "draft"),
                int(payload.get("module_count", 4)),
                json.dumps(payload.get("modules", [])),
                int(payload.get("lessons_count", 8)),
                float(payload.get("hours", 12)),
                0,
                0,
                0,
                0,
                payload.get("prerequisite_course_id"),
                now_local(),
                course_org_id,
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="course.create",
            target_type="course",
            target_id=new_id,
            message=f"{actor['full_name']} created course {payload['name']}",
            accent="emerald",
            result="success",
            org_id=course_org_id,
        )
        conn.commit()
        return get_course(new_id, org_id=course_org_id) or {}


def archive_course(course_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not row:
            raise ValueError("Course not found.")
        course = dict(row)
        conn.execute(
            "UPDATE courses SET status = 'archived' WHERE id = ?",
            (course_id,),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="course.archive",
            target_type="course",
            target_id=course_id,
            message=f"{actor['full_name']} archived course {course['name']}",
            accent="red",
            result="archived",
        )
        conn.commit()
        return get_course(course_id) or {}


def _is_allowed_domain(conn: sqlite3.Connection, email: str) -> bool:
    domain = email.split("@")[-1].lower()
    row = conn.execute(
        "SELECT 1 FROM allowed_domains WHERE lower(domain) = lower(?)",
        (domain,),
    ).fetchone()
    return row is not None


def _default_progress_for_category(category_slug: str, total_courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    progress = []
    for index, course in enumerate(total_courses):
        progress.append(
            {
                "course_id": course["id"],
                "progress": 0,
                "status": "in_progress" if index == 0 else ("locked" if course["tier"] == "Advanced" else "not_started"),
                "current_lesson": None,
            }
        )
    return progress


def create_manual_enrollment(payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
    category_slug = payload["category_slug"]
    with get_conn() as conn:
        category = conn.execute("SELECT * FROM categories WHERE slug = ?", (category_slug,)).fetchone()
        if not category:
            raise ValueError("Category not found.")
        category_org_id = _extract_org_id(category) or _extract_org_id(actor) or 1
        course_rows = [
            serialize_course(row)
            for row in conn.execute(
                """
                SELECT * FROM courses
                WHERE category_slug = ? AND status != 'archived' AND org_id = ?
                ORDER BY moodle_course_id, name
                """,
                (category_slug, category_org_id),
            ).fetchall()
        ]
        selected_course_ids = payload.get("course_ids") or [course["id"] for course in course_rows]
        selected_courses = [course for course in course_rows if course["id"] in selected_course_ids]
        if not selected_courses:
            raise ValueError("Select at least one course.")

        user_id = f"user-{slugify(payload['full_name'])}"
        existing = conn.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?)",
            (payload["email"],),
        ).fetchone()
        domain_warning = None
        if not _is_allowed_domain(conn, payload["email"]):
            domain_warning = "Email domain is not on the allowed self-enrol list."

        if existing:
            user_id = existing["id"]
            existing_user = conn.execute(
                "SELECT org_id, organization_id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            existing_org_id = _extract_org_id(existing_user)
            if existing_org_id is not None and existing_org_id != category_org_id:
                raise ValueError("This user belongs to another organization.")
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, category_scope = ?, enrollment_type = ?, total_courses = ?, current_course_id = ?,
                    course_progress_json = ?, organization_id = ?, org_id = ?
                WHERE id = ?
                """,
                (
                    payload["full_name"],
                    category_slug,
                    payload.get("enrollment_type", "manual"),
                    len(selected_courses),
                    selected_courses[0]["id"],
                    json.dumps(_default_progress_for_category(category_slug, selected_courses)),
                    category_org_id,
                    category_org_id,
                    user_id,
                ),
            )
        else:
            username = slugify(payload["full_name"]).replace("-", ".")
            conn.execute(
                """
            INSERT INTO users (
                id, username, email, full_name, role, category_scope, password_hash,
                avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                pal_task_completion_pct, streak_days, courses_completed, total_courses,
                cohort_rank, enrollment_type, current_course_id, course_progress_json, created_at,
                last_login, organization_id, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    username,
                    payload["email"].lower(),
                    payload["full_name"],
                    "learner",
                    category_slug,
                    hash_password(payload.get("password", "Learner@1234")),
                    initials(payload["full_name"]),
                    "#2563EB",
                    "#7C3AED",
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    len(selected_courses),
                    None,
                    payload.get("enrollment_type", "manual"),
                    selected_courses[0]["id"],
                    json.dumps(_default_progress_for_category(category_slug, selected_courses)),
                    now_local(),
                    None,
                    category_org_id,
                    category_org_id,
                ),
            )

        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="enrol.manual",
            target_type="user",
            target_id=user_id,
            message=f"{actor['full_name']} manually enrolled {payload['full_name']} -> {category_slug.upper()}",
            accent="brand",
            result="success",
            org_id=category_org_id,
        )
        _insert_activity(
            conn,
            user_id=user_id,
            category_slug=category_slug,
            icon="plus",
            accent="brand",
            message=f"{payload['full_name']} was enrolled into {category_slug.upper()} by admin",
        )
        _insert_notification(
            conn,
            user_id=user_id,
            title="Enrollment confirmed",
            body=f"You have been enrolled into the {category_slug.upper()} learning path.",
        )
        conn.commit()

    response = fetch_user_by_id(user_id) or {}
    response["domain_warning"] = domain_warning
    return response


def create_self_enrollment_request(payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
    email = payload["email"].strip().lower()
    domain = email.split("@")[-1]
    request_id = f"req-{slugify(payload['full_name'])}-{uuid.uuid4().hex[:6]}"
    with get_conn() as conn:
        category_org_id = _lookup_category_org_id(conn, payload["category_slug"])
        if category_org_id is None:
            raise ValueError("Category organization not found.")
        domain_allowed = _is_allowed_domain(conn, email)
        status = "pending" if domain_allowed else "rejected"
        reason = None if domain_allowed else "not a company member"
        conn.execute(
            """
            INSERT INTO enrollment_requests (
                id, full_name, email, category_slug, request_type, company_domain,
                domain_verified, status, requested_at, reviewed_by, reviewed_at, rejection_reason, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id,
                payload["full_name"],
                email,
                payload["category_slug"],
                "self",
                domain,
                int(domain_allowed),
                status,
                now_local(),
                None if domain_allowed else (actor["id"] if actor else None),
                None if domain_allowed else now_local(),
                reason,
                category_org_id,
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"] if actor else None,
            actor_name=actor["full_name"] if actor else payload["full_name"],
            action="enrol.self",
            target_type="request",
            target_id=request_id,
            message=f"{payload['full_name']} requested self-enrolment for {payload['category_slug'].upper()}",
            accent="emerald" if domain_allowed else "red",
            result="pending" if domain_allowed else "failure",
            org_id=category_org_id,
        )
        conn.commit()
    if not domain_allowed:
        raise PermissionError("not a company member")
    requests = list_enrollment_requests(limit=1, org_id=category_org_id)
    return requests[0]


def approve_enrollment_request(request_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM enrollment_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if not row:
            raise ValueError("Enrollment request not found.")
        request = dict(row)
        if request["status"] not in {"pending"}:
            raise ValueError("Only pending requests can be approved.")
        request_org_id = request.get("org_id") or _lookup_category_org_id(conn, request["category_slug"]) or 1
        actor_org_id = _extract_org_id(actor)
        if not actor.get("is_platform_admin") and actor_org_id != request_org_id:
            raise ValueError("You do not have permission to approve users outside your organization.")

        course_rows = [
            serialize_course(course)
            for course in conn.execute(
                """
                SELECT * FROM courses
                WHERE category_slug = ? AND status != 'archived' AND org_id = ?
                ORDER BY moodle_course_id, name
                """,
                (request["category_slug"], request_org_id),
            ).fetchall()
        ]
        user_id = f"user-{slugify(request['full_name'])}"
        existing = conn.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (request["email"],)).fetchone()
        if existing:
            user_id = existing["id"]
            existing_user = conn.execute(
                "SELECT org_id, organization_id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            existing_org_id = _extract_org_id(existing_user)
            if existing_org_id is not None and existing_org_id != request_org_id:
                raise ValueError("This user belongs to another organization.")
            conn.execute(
                """
                UPDATE users
                SET category_scope = ?, role = 'learner', enrollment_type = ?, is_active = 1,
                    current_course_id = ?, total_courses = ?, course_progress_json = ?,
                    organization_id = ?, org_id = ?
                WHERE id = ?
                """,
                (
                    request["category_slug"],
                    request["request_type"],
                    course_rows[0]["id"] if course_rows else None,
                    len(course_rows),
                    json.dumps(_default_progress_for_category(request["category_slug"], course_rows)),
                    request_org_id,
                    request_org_id,
                    user_id,
                ),
            )
        else:
            username = slugify(request["full_name"]).replace("-", ".")
            conn.execute(
                """
            INSERT INTO users (
                id, username, email, full_name, role, category_scope, password_hash,
                avatar_initials, gradient_start, gradient_end, is_active, pal_score,
                pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                pal_task_completion_pct, streak_days, courses_completed, total_courses,
                cohort_rank, enrollment_type, current_course_id, course_progress_json, created_at,
                last_login, organization_id, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    username,
                    request["email"],
                    request["full_name"],
                    "learner",
                    request["category_slug"],
                    hash_password("Learner@1234"),
                    initials(request["full_name"]),
                    "#2563EB",
                    "#7C3AED",
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    len(course_rows),
                    None,
                    request["request_type"],
                    course_rows[0]["id"] if course_rows else None,
                    json.dumps(_default_progress_for_category(request["category_slug"], course_rows)),
                    now_local(),
                    None,
                    request_org_id,
                    request_org_id,
                ),
            )

        conn.execute(
            """
            UPDATE enrollment_requests
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?, rejection_reason = NULL
            WHERE id = ?
            """,
            (actor["id"], now_local(), request_id),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="enrol.approve",
            target_type="request",
            target_id=request_id,
            message=f"{actor['full_name']} approved enrollment for {request['full_name']}",
            accent="emerald",
            result="success",
            org_id=request_org_id,
        )
        _insert_activity(
            conn,
            user_id=user_id,
            category_slug=request["category_slug"],
            icon="plus",
            accent="emerald",
            message=f"{request['full_name']} was approved into {request['category_slug'].upper()}",
        )
        _insert_notification(
            conn,
            user_id=user_id,
            title="Enrollment approved",
            body=f"Your request for {request['category_slug'].upper()} has been approved.",
        )
        conn.commit()
        return list_enrollment_requests(limit=1, statuses=["approved"], org_id=request_org_id)[0]


def reject_enrollment_request(request_id: str, actor: dict[str, Any], reason: str | None = None) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM enrollment_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if not row:
            raise ValueError("Enrollment request not found.")
        request = dict(row)
        request_org_id = request.get("org_id") or _lookup_category_org_id(conn, request["category_slug"]) or 1
        actor_org_id = _extract_org_id(actor)
        if not actor.get("is_platform_admin") and actor_org_id != request_org_id:
            raise ValueError("You do not have permission to reject users outside your organization.")
        rejection_reason = reason or request.get("rejection_reason") or "rejected by admin"
        conn.execute(
            """
            UPDATE enrollment_requests
            SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, rejection_reason = ?
            WHERE id = ?
            """,
            (actor["id"], now_local(), rejection_reason, request_id),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="enrol.reject",
            target_type="request",
            target_id=request_id,
            message=f"{actor['full_name']} denied enrollment for {request['full_name']}",
            accent="red",
            result=rejection_reason,
            org_id=request_org_id,
        )
        conn.commit()
        return {
            "id": request_id,
            "status": "rejected",
            "rejection_reason": rejection_reason,
        }


def approve_enrollment_requests_batch(request_ids: list[str], actor: dict[str, Any]) -> dict[str, Any]:
    approved = 0
    for request_id in request_ids:
        try:
            approve_enrollment_request(request_id, actor)
            approved += 1
        except ValueError:
            continue
    return {"approved": approved}


def create_or_update_task(payload: dict[str, Any], actor: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:
    assigned_label = payload.get("assigned_label") or "All learners"
    with get_conn() as conn:
        task_org_id = (
            _lookup_category_org_id(conn, payload.get("category_slug"))
            or _extract_org_id(actor)
            or 1
        )
        if task_id:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                raise ValueError("Task not found.")
            existing_org_id = dict(row).get("org_id")
            actor_org_id = _extract_org_id(actor)
            if not actor.get("is_platform_admin") and actor_org_id is not None and existing_org_id != actor_org_id:
                raise ValueError("You do not have access to this organization.")
            conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, assigned_label = ?, assigned_to_user_id = ?,
                    assignment_scope = ?, category_slug = ?, due_at = ?, status = ?, notes = ?, is_cross_category = ?,
                    org_id = ?
                WHERE id = ?
                """,
                (
                    payload["title"],
                    payload.get("description", ""),
                    assigned_label,
                    payload.get("assigned_to_user_id"),
                    payload.get("assignment_scope", "individual"),
                    payload.get("category_slug", "ats"),
                    payload.get("due_at"),
                    payload.get("status", "pending"),
                    payload.get("notes", ""),
                    int(payload.get("is_cross_category", False)),
                    task_org_id,
                    task_id,
                ),
            )
            _insert_audit(
                conn,
                actor_id=actor["id"],
                actor_name=actor["full_name"],
                action="task.update",
                target_type="task",
                target_id=task_id,
                message=f"{actor['full_name']} updated task {payload['title']}",
                accent="violet",
                result="success",
                org_id=task_org_id,
            )
            conn.commit()
            rows = list_tasks(org_id=task_org_id)
            return next(task for task in rows if task["id"] == task_id)

        task_id = f"task-{slugify(payload['title'])}-{uuid.uuid4().hex[:6]}"
        conn.execute(
            """
            INSERT INTO tasks (
                id, title, description, assigned_label, assigned_to_user_id, assignment_scope,
                category_slug, due_at, status, created_at, assigned_by, notes, is_cross_category, org_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                payload["title"],
                payload.get("description", ""),
                assigned_label,
                payload.get("assigned_to_user_id"),
                payload.get("assignment_scope", "individual"),
                payload.get("category_slug", "ats"),
                payload.get("due_at"),
                payload.get("status", "pending"),
                now_local(),
                actor["id"],
                payload.get("notes", ""),
                int(payload.get("is_cross_category", False)),
                task_org_id,
            ),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="task.assign",
            target_type="task",
            target_id=task_id,
            message=f"{actor['full_name']} assigned task {payload['title']}",
            accent="teal",
            result="success",
            org_id=task_org_id,
        )
        if payload.get("assigned_to_user_id"):
            _insert_notification(
                conn,
                user_id=payload["assigned_to_user_id"],
                title="New task assigned",
                body=f"{payload['title']} is due on {payload.get('due_at') or 'soon'}.",
            )
        _insert_activity(
            conn,
            user_id=payload.get("assigned_to_user_id"),
            category_slug=payload.get("category_slug"),
            icon="launch",
            accent="teal",
            message=f"Admin assigned task '{payload['title']}' to {assigned_label}",
        )
        conn.commit()
        rows = list_tasks(org_id=task_org_id)
        return next(task for task in rows if task["id"] == task_id)


def delete_task(task_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError("Task not found.")
        task = dict(row)
        actor_org_id = _extract_org_id(actor)
        if not actor.get("is_platform_admin") and actor_org_id is not None and task.get("org_id") != actor_org_id:
            raise ValueError("You do not have access to this organization.")
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="task.delete",
            target_type="task",
            target_id=task_id,
            message=f"{actor['full_name']} deleted task {task['title']}",
            accent="red",
            result="archived",
            org_id=task.get("org_id"),
        )
        conn.commit()
        return task


def submit_task(task_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError("Task not found.")
        task = dict(row)
        actor_org_id = _extract_org_id(actor)
        if not actor.get("is_platform_admin") and actor_org_id is not None and task.get("org_id") != actor_org_id:
            raise ValueError("You do not have access to this organization.")
        conn.execute(
            "UPDATE tasks SET status = 'submitted' WHERE id = ?",
            (task_id,),
        )
        _insert_activity(
            conn,
            user_id=actor["id"],
            category_slug=actor.get("category_scope"),
            icon="check",
            accent="emerald",
            message=f"{actor['full_name']} submitted task {task['title']}",
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(updated)


def update_user_role(user_id: str, role: str, actor: dict[str, Any], category_scope: str | None = None) -> dict[str, Any]:
    normalized_role = normalize_role(role)
    if is_tenant_super_admin_role(normalized_role):
        category_scope = None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("User not found.")
        conn.execute(
            "UPDATE users SET role = ?, category_scope = ? WHERE id = ?",
            (normalized_role, category_scope, user_id),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="user.role",
            target_type="user",
            target_id=user_id,
            message=f"{actor['full_name']} changed role for {dict(row)['full_name']}",
            accent="violet",
            result="success",
        )
        conn.commit()
        return fetch_user_by_id(user_id) or {}


def set_user_active(user_id: str, is_active: bool, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("User not found.")
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (int(is_active), user_id),
        )
        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="user.activate" if is_active else "user.deactivate",
            target_type="user",
            target_id=user_id,
            message=f"{actor['full_name']} {'activated' if is_active else 'deactivated'} {dict(row)['full_name']}",
            accent="emerald" if is_active else "red",
            result="success",
        )
        conn.commit()
        return fetch_user_by_id(user_id) or {}


def soft_delete_user(user_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    return set_user_active(user_id, False, actor)


def get_user_activity(user_id: str) -> list[dict[str, Any]]:
    return list_activity_entries(user_id=user_id, limit=20)


def recompute_pal(category_slug: str | None = None, org_id: int | None = None) -> dict[str, Any]:
    clauses = [f"role IN ({SQL_LEARNER_ROLES})"]
    params: list[Any] = []
    if category_slug:
        clauses.append("category_scope = ?")
        params.append(category_slug)
    if org_id is not None:
        clauses.append("org_id = ?")
        params.append(org_id)

    where = " AND ".join(clauses)
    updated = 0
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM users WHERE {where}", params).fetchall()
        for row in rows:
            user = dict(row)
            hours_pct = min((user["pal_time_spent_hours"] / 50) * 100, 100)
            streak_pct = min((user["streak_days"] / 30) * 100, 100)
            pal_score = round(
                (user["pal_completion_pct"] * 0.35)
                + (user["pal_quiz_avg"] * 0.30)
                + (user["pal_task_completion_pct"] * 0.20)
                + (hours_pct * 0.10)
                + (streak_pct * 0.05),
                2,
            )
            conn.execute(
                "UPDATE users SET pal_score = ? WHERE id = ?",
                (pal_score, user["id"]),
            )
            updated += 1
        conn.commit()
    return {"updated": updated, "category_slug": category_slug or "all", "org_id": org_id}


def list_pal_leaderboard(
    category_slug: str,
    *,
    limit: int | None = None,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    params: list[Any] = [category_slug]
    sql = """
        SELECT * FROM users
        WHERE role IN ({learner_roles}) AND is_active = 1 AND category_scope = ?
        ORDER BY pal_score DESC, full_name
    """.format(learner_roles=SQL_LEARNER_ROLES)
    if org_id is not None:
        sql = """
        SELECT * FROM users
        WHERE role IN ({learner_roles}) AND is_active = 1 AND category_scope = ? AND org_id = ?
        ORDER BY pal_score DESC, full_name
        """.format(learner_roles=SQL_LEARNER_ROLES)
        params.append(org_id)
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [serialize_user(row) for row in rows if row]


def get_pal_distribution(category_slug: str, org_id: int | None = None) -> list[dict[str, Any]]:
    if category_slug == "ats":
        return ATS_STATS_CONFIG["pal_distribution"]
    leaderboard = list_pal_leaderboard(category_slug, org_id=org_id)
    buckets = [
        ("90-100%", 90, 100, "emerald"),
        ("75-89%", 75, 89, "brand"),
        ("60-74%", 60, 74, "amber"),
        ("45-59%", 45, 59, "amber"),
        ("Below 45%", 0, 44, "red"),
    ]
    result = []
    total = max(len(leaderboard), 1)
    for label, low, high, color in buckets:
        count = sum(1 for learner in leaderboard if low <= learner["pal_score"] <= high)
        result.append(
            {
                "range": label,
                "count": count,
                "width": round((count / total) * 100),
                "color": color,
            }
        )
    return result


def get_pal_user_detail(user_id: str, org_id: int | None = None) -> dict[str, Any]:
    user = fetch_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    if org_id is not None and _extract_org_id(user) != org_id:
        raise ValueError("User not found.")
    return {
        "user": user,
        "metrics": {
            "completion_pct": user["pal_completion_pct"],
            "quiz_avg": user["pal_quiz_avg"],
            "time_spent_hours": user["pal_time_spent_hours"],
            "task_completion_pct": user["pal_task_completion_pct"],
            "streak_days": user["streak_days"],
            "pal_score": user["pal_score"],
        },
        "course_progress": user["course_progress"],
    }


def build_launch_payload(course_id: str, viewer: dict[str, Any]) -> dict[str, Any]:
    course = get_course(course_id, org_id=_extract_org_id(viewer))
    if not course:
        raise ValueError("Course not found.")
    moodle_url = os.getenv("MOODLE_URL", "http://localhost:8082").rstrip("/")
    return {
        "course_id": course["id"],
        "course_name": course["name"],
        "launch_url": f"{moodle_url}/course/view.php?id={course['moodle_course_id']}",
        "mode": "direct",
        "requested_by": viewer["full_name"],
    }


def build_super_admin_dashboard(org_id: int | None = None) -> dict[str, Any]:
    categories = list_categories(include_archived=False, org_id=org_id)
    admins = list_admins(org_id=org_id)
    leaderboard = []
    for category in categories:
        leaderboard.extend(list_pal_leaderboard(category["slug"], limit=4, org_id=org_id))
    leaderboard = sorted(leaderboard, key=lambda item: item["pal_score"], reverse=True)[:6]
    enrollment_requests = list_enrollment_requests(limit=5, org_id=org_id)
    enrollment_rows = [
        {
            "full_name": request["full_name"],
            "category": request["category_slug"].upper(),
            "type": request["request_type"],
            "status": request["status"].title(),
            "request_id": request["id"],
        }
        for request in enrollment_requests
    ]
    return {
        "kpis": {
            "total_categories": len(categories),
            "total_courses": len(list_courses(include_archived=False, org_id=org_id)),
            "total_learners": count_active_learners(org_id=org_id),
            "pending_approvals": count_pending_approvals(org_id=org_id),
            "pending_verifications": count_pending_signups(org_id=org_id),
        },
        "categories": categories,
        "admins": admins,
        "leaderboard": leaderboard,
        "analytics": {
            "learners_per_category": [
                {"category": category["name"], "value": category["total_learners"], "color": category["accent_color"]}
                for category in categories
            ],
            "avg_pal_per_category": [
                {"category": category["name"], "value": category["avg_pal"], "color": category["accent_color"]}
                for category in categories
            ],
        },
        "enrollment_audit": {
            "rows": enrollment_rows,
            "visible_pending_ids": [request["id"] for request in enrollment_requests if request["status"] in {"pending", "flagged"}],
        },
        "audit_log": list_audit_entries(limit=10, org_id=org_id),
        "tasks": [task for task in list_tasks(org_id=org_id) if task["is_cross_category"]],
    }


def build_category_admin_dashboard(category_slug: str, org_id: int | None = None) -> dict[str, Any]:
    category = get_category(category_slug, org_id=org_id)
    if not category:
        raise ValueError("Category not found.")
    category_org_id = _extract_org_id(category)
    all_courses = list_courses(category_slug, include_archived=False, org_id=category_org_id)
    learners = list_users(role="learner", category_slug=category_slug, org_id=category_org_id)["users"]
    pending_requests = list_enrollment_requests(
        category_slug=category_slug,
        statuses=["pending", "flagged"],
        org_id=category_org_id,
    )
    leaderboard = list_pal_leaderboard(category_slug, limit=4, org_id=category_org_id)
    tasks = [task for task in list_tasks(category_slug=category_slug, include_cross_category=False, org_id=category_org_id)]
    return {
        "category": category,
        "kpis": {
            "total_courses": len(all_courses),
            "active_learners": len(learners),
            "pending_enrollment": len(pending_requests),
            "pending_verifications": count_pending_signups(org_id=category_org_id),
            "avg_pal_score": round(sum(learner["pal_score"] for learner in learners[: len(learners) or 1]) / max(len(learners), 1), 2),
        },
        "courses": all_courses,
        "pending_enrollment": pending_requests,
        "learners": {
            "total": len(learners),
            "rows": learners,
        },
        "tasks": tasks,
        "pal": {
            "summary": {
                "avg_completion": 81,
                "avg_quiz_score": 85,
                "avg_time_hours": 30,
            },
            "leaderboard": leaderboard,
            "chart": [{"name": learner["full_name"], "score": learner["pal_score"]} for learner in list_pal_leaderboard(category_slug, org_id=category_org_id)],
        },
        "activity": list_activity_entries(category_slug=category_slug, limit=20, org_id=category_org_id),
    }


def build_stats_dashboard(category_slug: str, org_id: int | None = None) -> dict[str, Any]:
    category = get_category(category_slug, org_id=org_id)
    if not category:
        raise ValueError("Category not found.")
    category_org_id = _extract_org_id(category)
    leaderboard = list_pal_leaderboard(category_slug, limit=5, org_id=category_org_id)
    full_leaderboard = list_pal_leaderboard(category_slug, org_id=category_org_id)
    archived = list_users(role="learner", category_slug=category_slug, include_inactive=True, org_id=category_org_id)["users"]
    archived = [user for user in archived if not user["is_active"]]
    courses = list_courses(category_slug, include_archived=False, org_id=category_org_id)
    return {
        "category": category,
        "filters": {
            "course_filters": ATS_STATS_CONFIG["course_filters"],
            "learner_filters": ATS_STATS_CONFIG["learner_filters"],
        },
        "kpis": {
            "active_courses": 5,
            "enrolled_learners": len(list_users(role="learner", category_slug=category_slug, org_id=category_org_id)["users"]),
            "pending_learners": 3,
            "avg_pal_score": 81,
        },
        "course_completion": courses,
        "enrollment_trend": ATS_STATS_CONFIG["enrollment_trend"],
        "user_breakdown": ATS_STATS_CONFIG["user_breakdown"],
        "pal_distribution": ATS_STATS_CONFIG["pal_distribution"],
        "leaderboard": leaderboard,
        "full_leaderboard": full_leaderboard,
        "archived_message": "No archived learners at this time." if not archived else None,
        "heatmap_weights": ATS_STATS_CONFIG["heatmap_weights"],
        "recent_activity": list_activity_entries(category_slug=category_slug, limit=10, org_id=category_org_id),
        "insight": ATS_STATS_CONFIG["insight"],
    }


def build_learner_dashboard(user_id: str) -> dict[str, Any]:
    user = fetch_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    user_org_id = _extract_org_id(user)
    current_course = get_course(user["current_course_id"], org_id=user_org_id) if user.get("current_course_id") else None
    courses = []
    course_lookup = {
        course["id"]: course
        for course in list_courses(user["category_scope"], include_archived=False, org_id=user_org_id)
    }
    for progress in user["course_progress"]:
        course = course_lookup.get(progress["course_id"])
        if not course:
            continue
        courses.append(
            {
                **course,
                "progress": progress["progress"],
                "progress_status": progress["status"],
                "current_lesson": progress.get("current_lesson"),
            }
        )
    cohort = list_pal_leaderboard(user["category_scope"], limit=5, org_id=user_org_id)
    return {
        "profile": user,
        "hero": {
            "headline": f"Good morning, {user['full_name'].split()[0]}",
            "subtext": f"{user['courses_completed']} of {user['total_courses']} courses completed - keep your streak alive.",
            "pal_score": user["pal_score"],
            "time_spent_hours": user["pal_time_spent_hours"],
            "streak_days": user["streak_days"],
            "rank": user["cohort_rank"] or 1,
            "current_course": current_course,
        },
        "stats": {
            "courses_completed": user["courses_completed"],
            "courses_remaining": max(user["total_courses"] - user["courses_completed"], 0),
            "avg_quiz_score": user["pal_quiz_avg"],
            "cohort_rank": user["cohort_rank"] or 1,
        },
        "courses": courses,
        "pal_breakdown": {
            "completion": user["pal_completion_pct"],
            "quiz_avg": user["pal_quiz_avg"],
            "time_on_task": user["pal_time_spent_hours"],
            "task_completion": user["pal_task_completion_pct"],
            "streak_days": user["streak_days"],
            "insight": "You're 6% away from a perfect PAL score. Complete the Advanced PostgreSQL final quiz to push past 99%!",
        },
        "tasks": list_tasks(viewer=user, category_slug=user["category_scope"], include_cross_category=False, org_id=user_org_id),
        "recommendation": {
            "up_next": current_course,
            "certificate_unlocked": False,
            "leaderboard": cohort,
        },
        "activity": list_activity_entries(user_id=user_id, category_slug=user["category_scope"], limit=8, org_id=user_org_id),
        "notifications": list_notifications(user_id),
    }


def get_system_settings() -> dict[str, Any]:
    with get_conn() as conn:
        domains = conn.execute("SELECT domain, label FROM allowed_domains ORDER BY domain").fetchall()
    return {
        "moodle_url": os.getenv("MOODLE_URL", "http://localhost:8082"),
        "api_version": "5.0.0",
        "allowed_domains": [dict(row) for row in domains],
        "category_slugs": [category["slug"] for category in list_categories(include_archived=True)],
    }


# ── Signup & Verification Store ──────────────────────────────────────────────


SIGNUP_ROLES = {
    "college": [
        {"value": "student", "label": "Student", "description": "Enrolled student at the college"},
        {"value": "teacher", "label": "Teacher", "description": "Faculty member"},
        {"value": "admin", "label": "College Admin", "description": "Administrative staff"},
        {"value": "college_admin", "label": "College Super Admin", "description": "Top-level college administrator"},
    ],
    "company": [
        {"value": "intern", "label": "Intern", "description": "Internship program participant"},
        {"value": "employee", "label": "Employee", "description": "Full-time or part-time employee"},
        {"value": "project_admin", "label": "Project Admin", "description": "Project-level administrator"},
        {"value": "company_admin", "label": "Company Admin", "description": "Top-level company administrator"},
    ],
}

_ROLE_TO_SYSTEM_ROLE = {
    "student": "learner",
    "intern": "learner",
    "teacher": "category_admin",
    "employee": "learner",
    "admin": "category_admin",
    "project_admin": "category_admin",
    "college_admin": "super_admin",
    "company_admin": "super_admin",
}


def get_signup_roles(domain_type: str) -> list[dict[str, str]]:
    return SIGNUP_ROLES.get(domain_type, [])


def create_pending_verification(payload: dict[str, Any]) -> dict[str, Any]:
    email = payload["email"].strip().lower()
    with get_conn() as conn:
        org_name = payload.get("organization_name", "").strip()
        if not org_name:
            raise ValueError("Organization Name is required.")
        
        org_row = conn.execute(
            "SELECT id, domain FROM organizations WHERE lower(name) = lower(?)",
            (org_name,)
        ).fetchone()
        
        if not org_row:
            raise ValueError(f"Organization '{org_name}' not found.")
            
        org_id = org_row["id"]
        org_domain = (org_row["domain"] or "").strip().lower()
        normalized_domain = org_domain.lstrip("@")

        if not normalized_domain:
            raise ValueError("Organization domain is not configured. Please contact your administrator.")

        if not email.endswith(f"@{normalized_domain}"):
            raise ValueError(f"Email domain must match the organization domain (@{normalized_domain}).")

        existing_user = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()
        if existing_user:
            raise ValueError("An account with this email already exists.")
        existing_pending = conn.execute(
            "SELECT 1 FROM pending_verifications WHERE lower(email) = lower(?) AND status = 'pending'",
            (email,),
        ).fetchone()
        if existing_pending:
            raise ValueError("A registration with this email is already pending review.")

        verification_id = f"pv-{str(uuid.uuid4())[:8]}"
        conn.execute(
            """
            INSERT INTO pending_verifications (
                id, email, full_name, password_hash, role_name, domain_type,
                organization_name, organization_id, phone, id_number, program, branch, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                verification_id,
                email,
                payload["full_name"],
                hash_password(payload["password"]),
                payload["role_name"],
                payload["domain_type"],
                org_name,
                org_id,
                payload.get("phone", ""),
                payload.get("id_number", ""),
                payload.get("program", ""),
                payload.get("branch", ""),
                "pending",
                now_local(),
            ),
        )
        conn.commit()
    return get_pending_verification(verification_id) or {}


def get_pending_verification(verification_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pending_verifications WHERE id = ? LIMIT 1",
            (verification_id,),
        ).fetchone()
        return dict(row) if row else None


def list_pending_verifications(
    *,
    status: str | None = None,
    domain_type: str | None = None,
    limit: int | None = None,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if domain_type:
        clauses.append("domain_type = ?")
        params.append(domain_type)
    if org_id is not None:
        clauses.append("organization_id = ?")
        params.append(org_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM pending_verifications
        {where}
        ORDER BY created_at DESC
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def count_pending_signups(org_id: int | None = None) -> int:
    with get_conn() as conn:
        if org_id is not None:
            row = conn.execute("SELECT COUNT(*) AS count FROM pending_verifications WHERE status = 'pending' AND organization_id = ?", (org_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS count FROM pending_verifications WHERE status = 'pending'").fetchone()
        return row["count"]


def approve_pending_verification(verification_id: str, actor: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pending_verifications WHERE id = ?",
            (verification_id,),
        ).fetchone()
        if not row:
            raise ValueError("Verification request not found.")
        pv = dict(row)
        if pv["status"] != "pending":
            raise ValueError(f"This request has already been {pv['status']}.")

        # Check actor org match
        actor_org = _extract_org_id(actor)
        if not actor.get("is_platform_admin") and actor_org != pv["organization_id"]:
            raise ValueError("You do not have permission to approve users outside your organization.")

        approved_role = _ROLE_TO_SYSTEM_ROLE.get(pv["role_name"], pv["role_name"])
        user = _create_user_record(
            conn,
            email=pv["email"],
            full_name=pv["full_name"],
            role=approved_role,
            password_hash_value=pv["password_hash"],
            org_id=pv["organization_id"],
            program=pv.get("program"),
            branch=pv.get("branch"),
            id_number=pv.get("id_number"),
        )

        conn.execute(
            """
            UPDATE pending_verifications
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (actor["id"], now_local(), verification_id),
        )

        conn.execute(
            """
            INSERT INTO admin_actions (admin_user_id, action_type, target_id, reason, created_at)
            VALUES (?,?,?,?,?)
            """,
            (actor["id"], "APPROVE_SIGNUP", verification_id, None, now_local()),
        )

        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="signup.approve",
            target_type="pending_verification",
            target_id=verification_id,
            message=f"{actor['full_name']} approved signup for {pv['full_name']} ({pv['role_name']})",
            accent="emerald",
            result="approved",
            org_id=pv["organization_id"],
        )

        _insert_activity(
            conn,
            user_id=None,
            category_slug=None,
            icon="check",
            accent="emerald",
            message=f"New {pv['role_name']} approved: {pv['full_name']}",
        )

        conn.commit()

    return {
        "status": "approved",
        "user_id": user["id"],
        "username": user["username"],
        "email": pv["email"],
        "full_name": pv["full_name"],
        "system_role": approved_role,
        "signup_role": pv["role_name"],
        "program": pv.get("program"),
        "branch": pv.get("branch"),
        "id_number": pv.get("id_number"),
    }


def reject_pending_verification(
    verification_id: str,
    actor: dict[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pending_verifications WHERE id = ?",
            (verification_id,),
        ).fetchone()
        if not row:
            raise ValueError("Verification request not found.")
        pv = dict(row)
        if pv["status"] != "pending":
            raise ValueError(f"This request has already been {pv['status']}.")

        rejection_reason = reason or "Your application did not meet the requirements."

        conn.execute(
            """
            UPDATE pending_verifications
            SET status = 'rejected', rejection_reason = ?, reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (rejection_reason, actor["id"], now_local(), verification_id),
        )

        conn.execute(
            """
            INSERT INTO admin_actions (admin_user_id, action_type, target_id, reason, created_at)
            VALUES (?,?,?,?,?)
            """,
            (actor["id"], "REJECT_SIGNUP", verification_id, rejection_reason, now_local()),
        )

        _insert_audit(
            conn,
            actor_id=actor["id"],
            actor_name=actor["full_name"],
            action="signup.reject",
            target_type="pending_verification",
            target_id=verification_id,
            message=f"{actor['full_name']} rejected signup for {pv['full_name']}: {rejection_reason}",
            accent="red",
            result="rejected",
        )

        conn.commit()

    return {
        "status": "rejected",
        "verification_id": verification_id,
        "email": pv["email"],
        "full_name": pv["full_name"],
        "role_name": pv["role_name"],
        "reason": rejection_reason,
    }


def update_user_moodle_id(user_id: str, moodle_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET moodle_id = ? WHERE id = ?", (moodle_id, user_id))
        conn.commit()
