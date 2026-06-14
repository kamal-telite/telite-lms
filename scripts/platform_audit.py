"""Phase A.5 platform integrity audit.

Run from the repository root:
    python scripts/platform_audit.py

The audit compares the live PostgreSQL schema with SQLAlchemy metadata,
checks tenant ownership expectations, verifies RLS status, and writes
JSON/Markdown reports into Project_docs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "telite-backend"
PROJECT_DOCS = ROOT / "Project_docs"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401  # Import all models so Base metadata is populated.
from app.models.base import Base


GLOBAL_TABLES = {
    "admin_actions",
    "alembic_version",
    "organizations",
    "platform_settings",
    "org_feature_flags",
    "allowed_domains",
}

TENANT_TABLES = {
    "activity_log",
    "alert_rules",
    "audit_log",
    "auth_sessions",
    "branding_assets",
    "branding_audit_logs",
    "branding_versions",
    "builder_activity_log",
    "categories",
    "certificates",
    "course_edit_locks",
    "course_modules",
    "course_progress",
    "course_reviews",
    "course_sections",
    "course_versions",
    "courses",
    "enrollment_requests",
    "grading_events",
    "grading_rubrics",
    "interactive_tracking",
    "learner_activity_log",
    "learner_events",
    "learning_path_courses",
    "learning_path_progress",
    "learning_paths",
    "lesson_block_progress",
    "lesson_blocks",
    "media_assets",
    "memberships",
    "module_progress",
    "moodle_sync_logs",
    "moodle_tenants",
    "notifications",
    "org_invitations",
    "organization_branding",
    "pal_quiz_scores",
    "pal_recommendations",
    "pal_topic_performance",
    "password_reset_tokens",
    "pending_verifications",
    "question_banks",
    "question_versions",
    "questions",
    "quiz_answers",
    "quiz_attempt_events",
    "quiz_attempt_questions",
    "quiz_attempts",
    "quiz_definitions",
    "quiz_settings",
    "role_permissions",
    "rubric_criteria",
    "tasks",
    "users",
}


@dataclass
class ColumnAudit:
    column_name: str
    db_type: str | None
    model_type: str | None
    status: str


@dataclass
class TableAudit:
    table_name: str
    status: str
    tenant_owned: bool
    has_org_id: bool
    org_id_nullable: bool | None
    foreign_key_exists: bool
    rls_enabled: bool
    database_column_types: dict[str, str]
    model_column_types: dict[str, str]
    model_type_match: bool
    api_routes_using_table: list[str]
    column_audit: list[ColumnAudit]
    failures: list[str]


def build_database_url() -> str:
    explicit = os.getenv("TELITE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit:
        return explicit.replace("postgresql://", "postgresql+psycopg://", 1)

    host = os.getenv("TELITE_POSTGRES_HOST") or os.getenv("POSTGRES_HOST") or "localhost"
    port = os.getenv("TELITE_POSTGRES_PORT") or os.getenv("POSTGRES_PORT") or "55432"
    db = os.getenv("TELITE_POSTGRES_DB") or os.getenv("POSTGRES_DB") or "telite_backend"
    user = os.getenv("TELITE_POSTGRES_USER") or os.getenv("POSTGRES_USER") or "postgres"
    password = os.getenv("TELITE_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or "postgres123"
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def normalize_db_type(raw_type: Any) -> str:
    if isinstance(raw_type, DateTime):
        return "timestamp with time zone" if raw_type.timezone else "timestamp without time zone"
    value = str(raw_type).lower()
    if "timestamp" in value:
        return "timestamp with time zone" if "time zone" in value else "timestamp without time zone"
    if value in {"character varying", "varchar"} or value.startswith(("character varying", "varchar")):
        return "string"
    if value in {"text"}:
        return "text"
    if value in {"integer", "int4"}:
        return "integer"
    if value in {"bigint", "int8"}:
        return "bigint"
    if value in {"boolean", "bool"}:
        return "boolean"
    if value in {"real", "double precision", "float"}:
        return "float"
    if value in {"json", "jsonb"}:
        return "json"
    if value.startswith("numeric"):
        return "numeric"
    return value


def normalize_model_type(raw_type: Any) -> str:
    if isinstance(raw_type, Boolean):
        return "boolean"
    if isinstance(raw_type, BigInteger):
        return "bigint"
    if isinstance(raw_type, Integer):
        return "integer"
    if isinstance(raw_type, DateTime):
        return "timestamp with time zone" if raw_type.timezone else "timestamp without time zone"
    if isinstance(raw_type, Text):
        return "text"
    if isinstance(raw_type, String):
        return "string"
    if isinstance(raw_type, Float):
        return "float"
    if isinstance(raw_type, Numeric):
        return "numeric"
    if isinstance(raw_type, JSON):
        return "json"
    return str(raw_type).lower()


def equivalent_type(db_type: str | None, model_type: str | None) -> bool:
    if db_type == model_type:
        return True
    if db_type in {"text", "string"} and model_type in {"text", "string"}:
        return True
    if db_type in {"integer", "bigint"} and model_type in {"integer", "bigint"}:
        return True
    if db_type == "real" and model_type == "float":
        return True
    return False


def load_rls_status(engine: Engine) -> dict[str, bool]:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                """
            )
        )
        return {row.relname: bool(row.relrowsecurity) for row in result}


def find_route_references(table_name: str) -> list[str]:
    references: list[str] = []
    model_table = Base.metadata.tables.get(table_name)
    needles = {table_name}
    if model_table is not None:
        for mapper in Base.registry.mappers:
            if mapper.local_table.name == table_name:
                needles.add(mapper.class_.__name__)

    for path in (BACKEND_ROOT / "app").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            text_body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text_body = path.read_text(encoding="utf-8", errors="ignore")
        if any(needle in text_body for needle in needles):
            references.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return sorted(references)


def audit_table(
    table_name: str,
    db_columns: dict[str, dict[str, Any]],
    model_columns: dict[str, Any],
    foreign_keys: list[dict[str, Any]],
    rls_enabled: bool,
) -> TableAudit:
    tenant_owned = table_name in TENANT_TABLES
    has_org_id = "org_id" in db_columns
    org_id_nullable = db_columns["org_id"]["nullable"] if has_org_id else None
    foreign_key_exists = any("org_id" in fk.get("constrained_columns", []) for fk in foreign_keys)

    database_column_types = {
        name: normalize_db_type(col["type"]) for name, col in sorted(db_columns.items())
    }
    model_column_types = {
        name: normalize_model_type(col.type) for name, col in sorted(model_columns.items())
    }

    column_audit: list[ColumnAudit] = []
    for column_name in sorted(set(database_column_types) | set(model_column_types)):
        db_type = database_column_types.get(column_name)
        model_type = model_column_types.get(column_name)
        if db_type is None:
            status = "MISSING_IN_DB"
        elif model_type is None:
            status = "MISSING_IN_MODEL"
        elif equivalent_type(db_type, model_type):
            status = "PASS"
        else:
            status = "TYPE_MISMATCH"
        column_audit.append(ColumnAudit(column_name, db_type, model_type, status))

    failures: list[str] = []
    if tenant_owned:
        if not has_org_id:
            failures.append("tenant-owned table is missing org_id")
        elif org_id_nullable:
            failures.append("tenant-owned table has nullable org_id")
        if not foreign_key_exists:
            failures.append("tenant-owned table is missing org_id foreign key")
        if not rls_enabled:
            failures.append("tenant-owned table does not have RLS enabled")

    if any(item.status in {"MISSING_IN_DB", "TYPE_MISMATCH"} for item in column_audit):
        failures.append("database schema does not match SQLAlchemy model")

    if table_name not in TENANT_TABLES and table_name not in GLOBAL_TABLES:
        failures.append("table is not classified in tenant ownership registry")

    model_type_match = not any(
        item.status in {"MISSING_IN_DB", "TYPE_MISMATCH"} for item in column_audit
    )
    status = "PASS" if not failures else "FAIL"

    return TableAudit(
        table_name=table_name,
        status=status,
        tenant_owned=tenant_owned,
        has_org_id=has_org_id,
        org_id_nullable=org_id_nullable,
        foreign_key_exists=foreign_key_exists,
        rls_enabled=rls_enabled,
        database_column_types=database_column_types,
        model_column_types=model_column_types,
        model_type_match=model_type_match,
        api_routes_using_table=find_route_references(table_name),
        column_audit=column_audit,
        failures=failures,
    )


def run_audit(engine: Engine) -> list[TableAudit]:
    inspector = inspect(engine)
    rls_status = load_rls_status(engine)
    db_table_names = set(inspector.get_table_names(schema="public"))
    model_table_names = set(Base.metadata.tables)
    audited_tables = sorted((db_table_names | model_table_names) - {"alembic_version"})

    results: list[TableAudit] = []
    for table_name in audited_tables:
        db_columns = {
            col["name"]: col for col in inspector.get_columns(table_name, schema="public")
        } if table_name in db_table_names else {}
        model_table = Base.metadata.tables.get(table_name)
        model_columns = dict(model_table.columns) if model_table is not None else {}
        foreign_keys = inspector.get_foreign_keys(table_name, schema="public") if table_name in db_table_names else []
        results.append(
            audit_table(
                table_name,
                db_columns,
                model_columns,
                foreign_keys,
                rls_status.get(table_name, False),
            )
        )
    return results


def health_gates(
    results: list[TableAudit],
    *,
    api_contract_status: str = "PENDING",
    dashboard_health_status: str = "PENDING",
) -> dict[str, str]:
    schema_ok = all(
        not any(item.status == "MISSING_IN_DB" for item in table.column_audit)
        for table in results
    )
    model_ok = all(table.model_type_match for table in results)
    tenant_ok = all(
        not table.tenant_owned
        or (table.has_org_id and table.org_id_nullable is False and table.foreign_key_exists)
        for table in results
    )
    rls_ok = all(not table.tenant_owned or table.rls_enabled for table in results)
    return {
        "Schema Audit": "PASS" if schema_ok else "FAIL",
        "Model Audit": "PASS" if model_ok else "FAIL",
        "Tenant Ownership Audit": "PASS" if tenant_ok else "FAIL",
        "RLS Isolation Audit": "PASS" if rls_ok else "FAIL",
        "API Contract Audit": api_contract_status,
        "Dashboard Health Audit": dashboard_health_status,
    }


def write_reports(results: list[TableAudit], gates: dict[str, str]) -> None:
    PROJECT_DOCS.mkdir(exist_ok=True)

    payload = {
        "health_gates": gates,
        "tables": [
            {
                **asdict(table),
                "column_audit": [asdict(item) for item in table.column_audit],
            }
            for table in results
        ],
    }
    (PROJECT_DOCS / "platform_audit_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Phase A.5 Platform Audit Report",
        "",
        "Generated by `python scripts/platform_audit.py`.",
        "",
        "## Health Gates",
        "",
        "| Gate | Status |",
        "|---|---|",
    ]
    for gate, status in gates.items():
        lines.append(f"| {gate} | {status} |")

    lines.extend(
        [
            "",
            "## Table Summary",
            "",
            "| Table | Status | Tenant Owned | org_id | org_id Nullable | FK | RLS | Model Match |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for table in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    table.table_name,
                    table.status,
                    "yes" if table.tenant_owned else "no",
                    "yes" if table.has_org_id else "no",
                    "yes" if table.org_id_nullable else "no",
                    "yes" if table.foreign_key_exists else "no",
                    "yes" if table.rls_enabled else "no",
                    "yes" if table.model_type_match else "no",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Failures", ""])
    for table in results:
        if table.failures:
            lines.append(f"### {table.table_name}")
            for failure in table.failures:
                lines.append(f"- {failure}")
            mismatches = [item for item in table.column_audit if item.status != "PASS"]
            for item in mismatches:
                lines.append(
                    f"- `{item.column_name}`: {item.status} "
                    f"(db={item.db_type}, model={item.model_type})"
                )
            lines.append("")

    (PROJECT_DOCS / "platform_audit_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def print_summary(results: list[TableAudit], gates: dict[str, str]) -> None:
    print("Health Gates")
    for gate, status in gates.items():
        print(f"  {gate}: {status}")
    print()
    print(f"{'TABLE':32} STATUS")
    for table in results:
        print(f"{table.table_name:32} {table.status}")
    print()
    print("Reports written:")
    print(f"  {PROJECT_DOCS / 'platform_audit_report.json'}")
    print(f"  {PROJECT_DOCS / 'platform_audit_report.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase A.5 platform integrity audit.")
    parser.add_argument("--no-fail", action="store_true", help="Always exit with status 0.")
    parser.add_argument(
        "--api-contract-status",
        choices=["PASS", "FAIL", "PENDING"],
        default="PENDING",
        help="Status from tests/test_dashboard_contracts.py.",
    )
    parser.add_argument(
        "--dashboard-health-status",
        choices=["PASS", "FAIL", "PENDING"],
        default="PENDING",
        help="Status from live dashboard verification.",
    )
    args = parser.parse_args()

    engine = create_engine(build_database_url(), future=True)
    results = run_audit(engine)
    gates = health_gates(
        results,
        api_contract_status=args.api_contract_status,
        dashboard_health_status=args.dashboard_health_status,
    )
    write_reports(results, gates)
    print_summary(results, gates)

    if args.no_fail:
        return 0
    return 0 if all(status == "PASS" for status in gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
