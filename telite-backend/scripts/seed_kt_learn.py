"""
seed_kt_learn.py — KT Learn Development Seed Specification

Run from the telite-backend directory:
    python scripts/seed_kt_learn.py

This script:
  1. Deletes all application data idempotently (schema/migrations untouched).
  2. Seeds KT Learn organization, users, categories, courses, and enrollments.
  3. Verifies expected row counts before exit.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from scripts.seed_permissions import seed_permissions

from app.core.password_utils import hash_password

SAFE_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}
PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging"}
PROTECTED_DATABASE_TOKENS = ("prod", "production", "live")
SEED_OVERRIDE_ENV = "TELITE_ALLOW_KT_LEARN_SEED"


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").lower().strip() in {"1", "true", "yes", "on"}


def validate_seed_target(db_url: str) -> None:
    environment = os.getenv("ENVIRONMENT", "development").lower().strip()
    if environment in PRODUCTION_LIKE_ENVIRONMENTS:
        raise RuntimeError(
            "Refusing to run KT Learn destructive seed in production-like "
            f"ENVIRONMENT={environment!r}."
        )

    if environment not in SAFE_ENVIRONMENTS and not _env_flag_enabled(SEED_OVERRIDE_ENV):
        raise RuntimeError(
            "Refusing to run KT Learn destructive seed because ENVIRONMENT is "
            f"{environment!r}. Set {SEED_OVERRIDE_ENV}=true only for an approved "
            "non-production reset target."
        )

    parsed = urlparse(db_url)
    target_parts = [
        (parsed.hostname or "").lower(),
        parsed.path.lstrip("/").lower(),
    ]
    for target in target_parts:
        if any(token in target for token in PROTECTED_DATABASE_TOKENS):
            raise RuntimeError(
                "Refusing to run KT Learn destructive seed against protected "
                f"database target {target!r}."
            )


def create_seed_engine(db_url: str):
    validate_seed_target(db_url)
    return create_engine(db_url)


def resolve_database_url() -> str:
    url = os.getenv("TELITE_MIGRATION_DATABASE_URL") or os.getenv("TELITE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if url:
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://").replace("postgresql://", "postgresql+psycopg://")

    host = os.getenv("TELITE_POSTGRES_HOST", "localhost")
    port = os.getenv("TELITE_POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("TELITE_POSTGRES_DB", "telite_backend")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    if password:
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql+psycopg://{user}@{host}:{port}/{db}"


DB_URL = resolve_database_url()
if not DB_URL:
    print("ERROR: Set TELITE_MIGRATION_DATABASE_URL or TELITE_DATABASE_URL in .env")
    sys.exit(1)

NOW = datetime.now(timezone.utc)

EXPECTED = {
    "organizations": 1,
    "users": 6,
    "categories": 2,
    "courses": 3,
    "course_sections": 6,
    "course_modules": 9,
    "lesson_blocks": 9,
    "enrollment_requests": 5,
}

DELETE_ORDER = [
    "assignment_submissions",
    "task_submissions",
    "task_reviews",
    "task_assignments",
    "certificates",
    "question_import_jobs",
    "question_tag_map",
    "question_tags",
    "question_categories",
    "role_permissions",
    "lesson_block_progress",
    "module_progress",
    "course_progress",
    "learner_events",
    "learner_activity_log",
    "interactive_tracking",
    "grading_events",
    "quiz_answers",
    "quiz_attempt_events",
    "quiz_attempt_questions",
    "quiz_attempts",
    "quiz_settings",
    "quiz_definitions",
    "question_versions",
    "questions",
    "question_banks",
    "rubric_criteria",
    "grading_rubrics",
    "builder_activity_log",
    "course_edit_locks",
    "course_reviews",
    "lesson_blocks",
    "course_versions",
    "course_modules",
    "course_sections",
    "learning_path_progress",
    "learning_path_courses",
    "learning_paths",
    "courses",
    "categories",
    "pal_topic_performance",
    "pal_recommendations",
    "pal_quiz_scores",
    "notifications",
    "tasks",
    "audit_log",
    "activity_log",
    "enrollment_requests",
    "auth_sessions",
    "password_reset_tokens",
    "pending_verifications",
    "org_invitations",
    "memberships",
    "media_assets",
    "users",
    "branding_audit_logs",
    "branding_assets",
    "branding_versions",
    "organization_branding",
    "allowed_domains",
    "platform_settings",
    "organizations",
]

USERS = [
    {
        "id": "globaladmin",
        "username": "globaladmin",
        "email": "globaladmin@ktlearn.local",
        "full_name": "Global Admin",
        "role": "platform_admin",
        "password": "GlobalAdmin@1234",
        "is_platform_admin": True,
        "category_scope": None,
        "initials": "GA",
    },
    {
        "id": "kt_superadmin",
        "username": "kt_superadmin",
        "email": "superadmin@ktlearn.local",
        "full_name": "KT Super Admin",
        "role": "super_admin",
        "password": "KTSuper@1234",
        "is_platform_admin": False,
        "category_scope": None,
        "initials": "KS",
    },
    {
        "id": "kt_category_admin",
        "username": "kt_category_admin",
        "email": "categoryadmin@ktlearn.local",
        "full_name": "KT Category Admin",
        "role": "category_admin",
        "password": "KTCategory@1234",
        "is_platform_admin": False,
        "category_scope": "backend-development",
        "initials": "KC",
    },
    {
        "id": "kt_learner_1",
        "username": "kt_learner_1",
        "email": "learner1@ktlearn.local",
        "full_name": "KT Learner 1",
        "role": "learner",
        "password": "KTLearner@1234",
        "is_platform_admin": False,
        "category_scope": "backend-development",
        "initials": "K1",
    },
    {
        "id": "kt_learner_2",
        "username": "kt_learner_2",
        "email": "learner2@ktlearn.local",
        "full_name": "KT Learner 2",
        "role": "learner",
        "password": "KTLearner@1234",
        "is_platform_admin": False,
        "category_scope": "devops-engineering",
        "initials": "K2",
    },
    {
        "id": "kt_learner_3",
        "username": "kt_learner_3",
        "email": "learner3@ktlearn.local",
        "full_name": "KT Learner 3",
        "role": "learner",
        "password": "KTLearner@1234",
        "is_platform_admin": False,
        "category_scope": "backend-development",
        "initials": "K3",
    },
]

CATEGORIES = [
    ("cat-backend", "Backend Development", "backend-development", "kt_category_admin", "#2563EB", 2),
    ("cat-devops", "DevOps Engineering", "devops-engineering", None, "#059669", 1),
]

COURSES = [
    ("course-python", "backend-development", "Python Foundations", "python-foundations", "Core Python syntax and tooling"),
    ("course-fastapi", "backend-development", "FastAPI Backend Essentials", "fastapi-backend-essentials", "Build APIs with FastAPI"),
    ("course-docker", "devops-engineering", "Docker and Deployment Basics", "docker-and-deployment-basics", "Container basics and deployment workflows"),
]

ENROLLMENTS = [
    ("enr-kt-1", "KT Learner 1", "learner1@ktlearn.local", "backend-development"),
    ("enr-kt-2", "KT Learner 1", "learner1@ktlearn.local", "devops-engineering"),
    ("enr-kt-3", "KT Learner 2", "learner2@ktlearn.local", "backend-development"),
    ("enr-kt-4", "KT Learner 2", "learner2@ktlearn.local", "devops-engineering"),
    ("enr-kt-5", "KT Learner 3", "learner3@ktlearn.local", "backend-development"),
]


def delete_all(session: Session) -> None:
    print("\nDeleting all existing data...")
    try:
        session.execute(text("TRUNCATE TABLE organizations CASCADE"))
        print("   - All data truncated via CASCADE from organizations.")
    except Exception as exc:
        print(f"   ! organizations: skipped ({exc.__class__.__name__})")
    
    # Truncate any remaining platform-level tables that might not cascade from organizations
    for table in ["question_banks", "questions", "question_versions", "users", "categories", "courses"]:
        try:
            with session.begin_nested():
                session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            pass
            
    session.commit()
    print("   Done.\n")


def seed_kt_learn(session: Session) -> None:
    print("Validating seed data for identifier collisions...")
    from app.repositories.user_repo import UserRepository
    repo = UserRepository(session)
    for user in USERS:
        try:
            repo.validate_identifier_uniqueness(user["email"], user["username"])
        except Exception as e:
            print(f"Data validation failed for {user['email']}: {e}")
            raise

    print("Seeding KT Learn data...\n")

    print("   Organization...")
    session.execute(
        text(
            """
            INSERT INTO organizations (id, name, type, domain, slug, status, plan, created_at)
            VALUES (1, 'KT Learn', 'company', 'ktlearn.local', 'kt-learn', 'active', 'pro', :now)
            """
        ),
        {"now": NOW},
    )
    session.execute(text("SELECT setval('organizations_id_seq', 10)"))

    session.execute(
        text(
            """
            INSERT INTO organization_branding (
                org_id, organization_id, primary_color, secondary_color, font_family, theme_mode, created_at
            ) VALUES (1, 1, '#2563EB', '#111827', 'Inter', 'light', :now)
            """
        ),
        {"now": NOW},
    )

    print("   Users and memberships...")
    for user in USERS:
        session.execute(
            text(
                """
                INSERT INTO users (
                    id, username, email, full_name, role, category_scope, password_hash,
                    avatar_initials, gradient_start, gradient_end,
                    is_active, is_platform_admin, status, theme_preference, org_id, created_at,
                    pal_score, pal_completion_pct, pal_quiz_avg, pal_time_spent_hours,
                    pal_task_completion_pct, streak_days, courses_completed, total_courses,
                    course_progress_json
                ) VALUES (
                    :id, :username, :email, :full_name, :role, :category_scope, :pw_hash,
                    :initials, '#2563EB', '#111827',
                    true, :is_platform, 'active', 'system', 1, :now,
                    0, 0, 0, 0, 0, 0, 0, 0, '[]'
                )
                """
            ),
            {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "category_scope": user["category_scope"],
                "pw_hash": hash_password(user["password"]),
                "is_platform": user["is_platform_admin"],
                "initials": user["initials"],
                "now": NOW,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO memberships (user_id, org_id, role, category_scope, status, created_at)
                VALUES (:uid, 1, :role, :category_scope, 'active', :now)
                """
            ),
            {
                "uid": user["id"],
                "role": user["role"],
                "category_scope": user["category_scope"],
                "now": NOW,
            },
        )

    print("   Categories...")
    for cat_id, name, slug, admin_uid, accent_color, planned_courses in CATEGORIES:
        session.execute(
            text(
                """
                INSERT INTO categories (
                    id, name, slug, status, accent_color, admin_user_id,
                    planned_courses, avg_pal_target, org_id, org_type, created_at
                ) VALUES (
                    :id, :name, :slug, 'active', :accent_color, :admin_uid,
                    :planned_courses, 0.0, 1, 'company', :now
                )
                """
            ),
            {
                "id": cat_id,
                "name": name,
                "slug": slug,
                "admin_uid": admin_uid,
                "accent_color": accent_color,
                "planned_courses": planned_courses,
                "now": NOW,
            },
        )

    print("   Courses, sections, modules, and blocks...")
    section_id = 1
    module_id = 1
    block_id = 1

    for course_id, cat_slug, name, slug, description in COURSES:
        session.execute(
            text(
                """
                INSERT INTO courses (
                    id, category_slug, name, slug, description, status, tier,
                    module_count, modules_json, lessons_count, hours,
                    enrolled_count, completion_rate, completion_count, avg_quiz_score,
                    price_paise, org_id, created_at
                ) VALUES (
                    :id, :cat_slug, :name, :slug, :description, 'published', 'Basic',
                    3, '[]', 3, 10,
                    0, 0, 0, 0,
                    0, 1, :now
                )
                """
            ),
            {
                "id": course_id,
                "cat_slug": cat_slug,
                "name": name,
                "slug": slug,
                "description": description,
                "now": NOW,
            },
        )

        section_ids: list[int] = []
        for section_num in range(1, 3):
            session.execute(
                text(
                    """
                    INSERT INTO course_sections (id, course_id, org_id, title, sort_order)
                    VALUES (:id, :course_id, 1, :title, :sort)
                    """
                ),
                {
                    "id": section_id,
                    "course_id": course_id,
                    "title": f"Section {section_num}",
                    "sort": section_num - 1,
                },
            )
            section_ids.append(section_id)
            section_id += 1

        for module_num in range(1, 4):
            section_ref = section_ids[0] if module_num <= 2 else section_ids[1]
            session.execute(
                text(
                    """
                    INSERT INTO course_modules (
                        id, course_id, section_id, section, status, title,
                        module_type, sort_order, org_id, created_at
                    ) VALUES (
                        :id, :course_id, :section_id, :section, 'published', :title,
                        'page', :sort, 1, :now
                    )
                    """
                ),
                {
                    "id": module_id,
                    "course_id": course_id,
                    "section_id": section_ref,
                    "section": module_num - 1,
                    "title": f"Module {module_num}",
                    "sort": module_num - 1,
                    "now": NOW,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO lesson_blocks (id, module_id, org_id, block_type, content, sort_order)
                    VALUES (:id, :module_id, 1, 'text', :content, 0)
                    """
                ),
                {
                    "id": block_id,
                    "module_id": module_id,
                    "content": f"Seeded lesson content for {name}, module {module_num}.",
                },
            )
            module_id += 1
            block_id += 1

    session.execute(text(f"SELECT setval('course_sections_id_seq', {section_id + 10})"))
    session.execute(text(f"SELECT setval('course_modules_id_seq', {module_id + 10})"))
    session.execute(text(f"SELECT setval('lesson_blocks_id_seq', {block_id + 10})"))

    print("   Enrollments...")
    reviewed_at = NOW.strftime("%Y-%m-%d %H:%M")
    requested_at = reviewed_at
    for enrollment_id, full_name, email, category_slug in ENROLLMENTS:
        session.execute(
            text(
                """
                INSERT INTO enrollment_requests (
                    id, full_name, email, category_slug, request_type, status, domain_verified,
                    requested_at, reviewed_by, reviewed_at, org_id, created_at
                ) VALUES (
                    :id, :full_name, :email, :category_slug, 'manual', 'approved', false,
                    :requested_at, 'kt_superadmin', :reviewed_at, 1, :now
                )
                """
            ),
            {
                "id": enrollment_id,
                "full_name": full_name,
                "email": email,
                "category_slug": category_slug,
                "requested_at": requested_at,
                "reviewed_at": reviewed_at,
                "now": NOW,
            },
        )

    session.commit()


def verify_counts(session: Session) -> bool:
    print("\nVerification:")
    ok = True
    for table, expected in EXPECTED.items():
        actual = session.execute(text(f"SELECT count(*) FROM {table}")).scalar()
        status = "OK" if actual == expected else "FAIL"
        print(f"   {status} {table}: expected {expected}, got {actual}")
        if actual != expected:
            ok = False
    return ok


def print_credentials() -> None:
    print("\nSeeded credentials:")
    for user in USERS:
        print(f"   {user['username']} / {user['password']} ({user['role']})")


def main() -> int:
    engine = create_seed_engine(DB_URL)
    print(f"Connected to: {engine.url}")
    with Session(engine) as session:
        delete_all(session)
        seed_kt_learn(session)
        
        # Seed permissions after data is created
        print("\nSeeding Role Permissions...")
        seed_permissions()
        
        if not verify_counts(session):
            print("\nSeed completed with verification failures.")
            return 1
    print_credentials()
    print("\nSeed completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
