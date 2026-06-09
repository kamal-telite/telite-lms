"""
reseed_fresh.py — Wipe all old seed data and insert comprehensive fresh data.

Run from the telite-backend directory:
    python scripts/reseed_fresh.py

This script:
  1. Connects to PostgreSQL via .env (TELITE_DATABASE_URL)
  2. Deletes ALL existing data (in correct FK order)
  3. Inserts fresh, consistent seed data for:
     - 2 Organizations (Tenant A / Tenant B) WITH slugs
     - OrganizationBranding for each org
     - Users: super_admin, category_admin, learners
     - Memberships
     - Categories with correct slugs matching org
     - Courses with sections, modules, and lesson blocks
     - Course versions
     - Learner events (HEARTBEAT, MODULE_STARTED, COURSE_COMPLETED)
     - Course progress records
     - Tasks, Audit log, Notifications
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── Resolve DB URL ────────────────────────────────────────────────────────────
DB_URL = os.getenv("TELITE_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    print("ERROR: Set TELITE_DATABASE_URL or DATABASE_URL in .env")
    sys.exit(1)

engine = create_engine(DB_URL)
print(f"✅ Connected to: {engine.url}")

# ── Password hashing (bcrypt) ─────────────────────────────────────────────────
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(pw: str) -> str:
        return pwd_context.hash(pw)
except ImportError:
    import bcrypt
    def hash_password(pw: str) -> str:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

ADMIN_PW = hash_password("Admin@1234")
LEARNER_PW = hash_password("Learner@1234")
SUPER_PW = hash_password("Super@1234")

NOW = datetime.now(timezone.utc)
YESTERDAY = NOW - timedelta(days=1)
LAST_WEEK = NOW - timedelta(days=7)

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 1: DELETE ALL DATA (reverse FK order)
# ══════════════════════════════════════════════════════════════════════════════

DELETE_ORDER = [
    # Progress & tracking
    "lesson_block_progress",
    "module_progress",
    "course_progress",
    "learner_events",
    "learner_activity_log",
    "interactive_tracking",
    # Quiz system
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
    # Builder
    "builder_activity_log",
    "course_edit_locks",
    "lesson_blocks",
    "course_versions",
    "course_modules",
    "course_sections",
    # Learning paths
    "learning_path_progress",
    "learning_path_courses",
    "learning_paths",
    # Course & category
    "courses",
    "categories",
    # PAL
    "pal_topic_performance",
    "pal_recommendations",
    "pal_quiz_scores",
    # User-related
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
    # Branding
    "branding_audit_logs",
    "branding_assets",
    "branding_versions",
    "organization_branding",
    # Org
    "allowed_domains",
    "platform_settings",
    "organizations",
]


def delete_all(session: Session):
    """Delete all data in correct FK order."""
    print("\n🗑️  Deleting all existing data...")
    for table in DELETE_ORDER:
        try:
            result = session.execute(text(f"DELETE FROM {table}"))
            if result.rowcount > 0:
                print(f"   ✗ {table}: {result.rowcount} rows deleted")
        except Exception as e:
            # Table might not exist yet — skip
            session.rollback()
            print(f"   ⚠ {table}: skipped ({e.__class__.__name__})")
    session.commit()
    print("   Done.\n")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 2: INSERT FRESH DATA
# ══════════════════════════════════════════════════════════════════════════════

def seed_all(session: Session):
    print("🌱 Seeding fresh data...\n")

    # ── 1. Organizations ──────────────────────────────────────────────────────
    print("   📦 Organizations...")
    session.execute(text("""
        INSERT INTO organizations (id, name, type, domain, slug, status, plan, created_at)
        VALUES
            (1, 'Telite Academy', 'college', 'telite.io', 'tenanta', 'active', 'pro', :now),
            (2, 'Nexus Corp', 'company', 'nexus.io', 'tenantb', 'active', 'free', :now)
    """), {"now": NOW})

    # Reset sequence
    session.execute(text("SELECT setval('organizations_id_seq', 10)"))

    # ── 2. Organization Branding ──────────────────────────────────────────────
    print("   🎨 Organization Branding...")
    session.execute(text("""
        INSERT INTO organization_branding (organization_id, primary_color, secondary_color, font_family, theme_mode, created_at)
        VALUES
            (1, '#2563EB', '#111827', 'Inter', 'light', :now),
            (2, '#059669', '#1F2937', 'Outfit', 'dark', :now)
    """), {"now": NOW})

    # ── 3. Users ──────────────────────────────────────────────────────────────
    print("   👤 Users...")
    users = [
        # Tenant A — Super Admin
        ("superadmin", "superadmin", "superadmin@telite.io", "Rajan Mehra", "super_admin", None, SUPER_PW, "RM", "#7C3AED", "#2563EB", 1),
        # Tenant A — Category Admin
        ("ca_tenanta", "ca_tenanta", "anika@telite.io", "Anika Kapoor", "category_admin", "tenanta", ADMIN_PW, "AK", "#2563EB", "#0891B2", 1),
        # Tenant A — Learners
        ("rahul", "rahul", "rahul@telite.io", "Rahul Singh", "learner", "tenanta", LEARNER_PW, "RS", "#7C3AED", "#2563EB", 1),
        ("neha", "neha", "neha@telite.io", "Neha Pillai", "learner", "tenanta", LEARNER_PW, "NP", "#2563EB", "#06B6D4", 1),
        ("arjun", "arjun", "arjun@telite.io", "Arjun Mehta", "learner", "tenanta", LEARNER_PW, "AM", "#059669", "#0891B2", 1),
        ("simran", "simran", "simran@telite.io", "Simran Kaur", "learner", "tenanta", LEARNER_PW, "SK", "#D97706", "#92400E", 1),
        ("dev", "dev", "dev@telite.io", "Dev Verma", "learner", "tenanta", LEARNER_PW, "DV", "#DC2626", "#92400E", 1),
        ("sneha", "sneha", "sneha@telite.io", "Sneha Rao", "learner", "tenanta", LEARNER_PW, "SR", "#0891B2", "#2563EB", 1),
        # Tenant B — Super Admin
        ("sa_tenantb", "sa_tenantb", "admin@nexus.io", "Alex Morgan", "super_admin", None, SUPER_PW, "AM", "#059669", "#065F46", 2),
        # Tenant B — Category Admin
        ("ca_tenantb", "ca_tenantb", "vikram@nexus.io", "Vikram Sethi", "category_admin", "tenantb", ADMIN_PW, "VS", "#059669", "#065F46", 2),
        # Tenant B — Learner
        ("lr_tenantb", "lr_tenantb", "learner@nexus.io", "Priya Sharma", "learner", "tenantb", LEARNER_PW, "PS", "#DC2626", "#92400E", 2),
    ]
    for uid, uname, email, full_name, role, cat_scope, pw_hash, initials, g_start, g_end, org_id in users:
        pal_score = 0.0
        streak = 0
        courses_completed = 0
        total_courses = 0
        cohort_rank = None
        enrollment_type = None

        if role == "learner" and org_id == 1:
            # Give Tenant A learners realistic PAL data
            idx = [u[0] for u in users if u[4] == "learner" and u[10] == 1].index(uid)
            pal_scores = [94, 88, 81, 62, 54, 91]
            streaks = [12, 10, 8, 4, 3, 9]
            completed = [5, 4, 3, 2, 2, 4]
            pal_score = pal_scores[idx] if idx < len(pal_scores) else 50
            streak = streaks[idx] if idx < len(streaks) else 2
            courses_completed = completed[idx] if idx < len(completed) else 1
            total_courses = 6
            cohort_rank = idx + 1
            enrollment_type = "manual" if idx % 2 == 0 else "self"

        session.execute(text("""
            INSERT INTO users (
                id, username, email, full_name, role, category_scope, password_hash,
                avatar_initials, gradient_start, gradient_end, is_active, is_platform_admin,
                status, pal_score, streak_days, courses_completed, total_courses,
                cohort_rank, enrollment_type, course_progress_json, org_id, created_at
            ) VALUES (
                :id, :username, :email, :full_name, :role, :cat_scope, :pw_hash,
                :initials, :g_start, :g_end, true, :is_platform,
                'active', :pal_score, :streak, :completed, :total,
                :cohort_rank, :enrollment_type, '[]', :org_id, :now
            )
        """), {
            "id": uid, "username": uname, "email": email, "full_name": full_name,
            "role": role, "cat_scope": cat_scope, "pw_hash": pw_hash,
            "initials": initials, "g_start": g_start, "g_end": g_end,
            "is_platform": role == "super_admin",
            "pal_score": pal_score, "streak": streak,
            "completed": courses_completed, "total": total_courses,
            "cohort_rank": cohort_rank, "enrollment_type": enrollment_type,
            "org_id": org_id, "now": NOW,
        })

    # ── 4. Memberships ────────────────────────────────────────────────────────
    print("   🔗 Memberships...")
    for uid, _, _, _, role, cat_scope, _, _, _, _, org_id in users:
        session.execute(text("""
            INSERT INTO memberships (user_id, org_id, role, category_scope, status, created_at)
            VALUES (:uid, :org_id, :role, :cat_scope, 'active', :now)
        """), {"uid": uid, "org_id": org_id, "role": role, "cat_scope": cat_scope, "now": NOW})

    # ── 5. Categories ─────────────────────────────────────────────────────────
    print("   📂 Categories...")
    categories = [
        ("cat-ats", "ATS Training", "tenanta", "ATS learning programs", "#2563EB", "ca_tenanta", 6, 1),
        ("cat-devops", "DevOps", "devops", "DevOps learning category", "#059669", None, 5, 1),
        ("cat-cloud", "Cloud Essentials", "cloud", "Cloud foundations", "#D97706", None, 3, 1),
        ("cat-nexus", "Nexus Training", "tenantb", "Nexus Corp training", "#059669", "ca_tenantb", 4, 2),
    ]
    for cat_id, name, slug, desc, color, admin_uid, planned, org_id in categories:
        session.execute(text("""
            INSERT INTO categories (id, name, slug, description, status, accent_color, admin_user_id, planned_courses, org_id, org_type, created_at)
            VALUES (:id, :name, :slug, :desc, 'active', :color, :admin, :planned, :org_id, 'college', :now)
        """), {"id": cat_id, "name": name, "slug": slug, "desc": desc, "color": color,
               "admin": admin_uid, "planned": planned, "org_id": org_id, "now": NOW})

    # ── 6. Courses ────────────────────────────────────────────────────────────
    print("   📚 Courses...")
    courses = [
        # Tenant A courses (category_slug = tenanta)
        ("course-frontend-basics", "tenanta", "Frontend Basics", "frontend-basics", "HTML · CSS · JS fundamentals", "Basic", "active", 4, 14, 18, 16, 88, 16, 86, 1),
        ("course-backend-basics", "tenanta", "Backend Basics", "backend-basics", "HTTP · APIs · service design", "Basic", "active", 4, 12, 20, 15, 72, 13, 79, 1),
        ("course-postgresql", "tenanta", "PostgreSQL", "postgresql", "Relational modeling and SQL", "Basic", "active", 4, 11, 16, 14, 65, 11, 74, 1),
        ("course-advanced-frontend", "tenanta", "Advanced Frontend", "advanced-frontend", "Modern UI architecture and React", "Advanced", "active", 4, 10, 22, 11, 54, 8, 69, 1),
        ("course-advanced-backend", "tenanta", "Advanced Backend", "advanced-backend", "Async processing, queues, caching", "Advanced", "active", 4, 10, 24, 9, 41, 5, 62, 1),
        ("course-advanced-postgresql", "tenanta", "Advanced PostgreSQL", "advanced-postgresql", "Window functions and production SQL", "Advanced", "draft", 4, 9, 19, 8, 28, 3, 58, 1),
        # Tenant B courses
        ("course-nexus-onboarding", "tenantb", "Nexus Onboarding", "nexus-onboarding", "Company onboarding program", "Basic", "active", 3, 8, 10, 10, 63, 6, 70, 2),
        ("course-nexus-advanced", "tenantb", "Nexus Advanced", "nexus-advanced", "Advanced company training", "Advanced", "active", 3, 7, 12, 6, 44, 3, 61, 2),
    ]
    for c_id, cat_slug, name, slug, desc, tier, status, mod_count, lessons, hours, enrolled, comp_rate, comp_count, avg_quiz, org_id in courses:
        modules_list = []
        session.execute(text("""
            INSERT INTO courses (
                id, category_slug, name, slug, description, tier, status,
                module_count, modules_json, lessons_count, hours,
                enrolled_count, completion_rate, completion_count, avg_quiz_score,
                org_id, created_at
            ) VALUES (
                :id, :cat_slug, :name, :slug, :desc, :tier, :status,
                :mod_count, :modules_json, :lessons, :hours,
                :enrolled, :comp_rate, :comp_count, :avg_quiz,
                :org_id, :now
            )
        """), {
            "id": c_id, "cat_slug": cat_slug, "name": name, "slug": slug, "desc": desc,
            "tier": tier, "status": status, "mod_count": mod_count,
            "modules_json": json.dumps(modules_list), "lessons": lessons, "hours": hours,
            "enrolled": enrolled, "comp_rate": comp_rate, "comp_count": comp_count,
            "avg_quiz": avg_quiz, "org_id": org_id, "now": NOW,
        })

    # ── 7. Course Sections ────────────────────────────────────────────────────
    print("   📑 Course Sections...")
    section_id = 1
    course_sections_map = {}  # course_id -> list of section_ids
    section_data = {
        "course-frontend-basics": ["HTML Essentials", "CSS Layout Systems", "JavaScript Basics", "DOM Manipulation"],
        "course-backend-basics": ["Request Lifecycle", "REST APIs", "Authentication Basics", "Debugging Services"],
        "course-postgresql": ["Schema Design", "Joins and Filters", "Aggregations", "Indexes"],
        "course-advanced-frontend": ["Component Architecture", "State Management", "Accessibility", "Performance Tuning"],
        "course-advanced-backend": ["Queues and Jobs", "Caching Strategies", "Observability", "Scaling Patterns"],
        "course-advanced-postgresql": ["Window Functions", "CTEs", "Query Plans", "Backups and Recovery"],
        "course-nexus-onboarding": ["Welcome", "Company Policies", "Tools Setup"],
        "course-nexus-advanced": ["Leadership", "Advanced Tools", "Best Practices"],
    }
    for course_id, section_titles in section_data.items():
        org_id = 1 if "nexus" not in course_id else 2
        sec_ids = []
        for sort_order, title in enumerate(section_titles):
            session.execute(text("""
                INSERT INTO course_sections (id, course_id, org_id, title, sort_order)
                VALUES (:id, :course_id, :org_id, :title, :sort_order)
            """), {"id": section_id, "course_id": course_id, "org_id": org_id,
                   "title": title, "sort_order": sort_order})
            sec_ids.append(section_id)
            section_id += 1
        course_sections_map[course_id] = sec_ids

    # Reset sequence
    session.execute(text(f"SELECT setval('course_sections_id_seq', {section_id + 10})"))

    # ── 8. Course Modules ─────────────────────────────────────────────────────
    print("   📦 Course Modules...")
    module_id = 1
    course_modules_map = {}  # course_id -> list of module_ids
    module_types = ["page", "url", "quiz", "page"]  # cycle through types

    for course_id, sec_ids in course_sections_map.items():
        org_id = 1 if "nexus" not in course_id else 2
        mod_ids = []
        for idx, sec_id in enumerate(sec_ids):
            mtype = module_types[idx % len(module_types)]
            title = section_data[course_id][idx]
            session.execute(text("""
                INSERT INTO course_modules (
                    id, course_id, section_id, section, status, title,
                    module_type, sort_order, org_id, created_at
                ) VALUES (
                    :id, :course_id, :section_id, :section, 'published', :title,
                    :mtype, :sort_order, :org_id, :now
                )
            """), {
                "id": module_id, "course_id": course_id, "section_id": sec_id,
                "section": idx, "title": title, "mtype": mtype,
                "sort_order": idx, "org_id": org_id, "now": NOW,
            })
            mod_ids.append(module_id)
            module_id += 1
        course_modules_map[course_id] = mod_ids

    session.execute(text(f"SELECT setval('course_modules_id_seq', {module_id + 10})"))

    # ── 9. Lesson Blocks ──────────────────────────────────────────────────────
    print("   🧱 Lesson Blocks...")
    block_id = 1
    for course_id, mod_ids in course_modules_map.items():
        org_id = 1 if "nexus" not in course_id else 2
        for mid in mod_ids:
            # 3 blocks per module: text intro, content, summary
            blocks = [
                ("text", f"Welcome to this module. This lesson covers the fundamentals.", 0),
                ("text", f"Here is the detailed content for this topic. Study carefully and review the key concepts.", 1),
                ("text", f"Summary: You've completed this section. Review the key takeaways before moving on.", 2),
            ]
            for btype, content, sort in blocks:
                session.execute(text("""
                    INSERT INTO lesson_blocks (id, module_id, org_id, block_type, content, sort_order)
                    VALUES (:id, :mid, :org_id, :btype, :content, :sort)
                """), {"id": block_id, "mid": mid, "org_id": org_id,
                       "btype": btype, "content": content, "sort": sort})
                block_id += 1

    session.execute(text(f"SELECT setval('lesson_blocks_id_seq', {block_id + 10})"))

    # ── 10. Course Versions ───────────────────────────────────────────────────
    print("   📋 Course Versions...")
    ver_id = 1
    for course_id in course_sections_map:
        org_id = 1 if "nexus" not in course_id else 2
        pub_user = "ca_tenanta" if org_id == 1 else "ca_tenantb"
        session.execute(text("""
            INSERT INTO course_versions (id, course_id, org_id, version_number, status, published_by, published_at, created_at)
            VALUES (:id, :course_id, :org_id, 1, 'published', :pub_user, :now, :now)
        """), {"id": ver_id, "course_id": course_id, "org_id": org_id,
               "pub_user": pub_user, "now": NOW})
        ver_id += 1

    session.execute(text(f"SELECT setval('course_versions_id_seq', {ver_id + 10})"))

    # ── 11. Course Progress ───────────────────────────────────────────────────
    print("   📊 Course Progress...")
    tenant_a_learners = ["rahul", "neha", "arjun", "simran", "dev", "sneha"]
    tenant_a_courses = [
        "course-frontend-basics", "course-backend-basics", "course-postgresql",
        "course-advanced-frontend", "course-advanced-backend", "course-advanced-postgresql",
    ]
    progress_map = {
        "rahul":  [100, 100, 100, 100, 100, 42],
        "neha":   [100, 100, 100, 100, 61, 0],
        "arjun":  [100, 100, 100, 53, 0, 0],
        "simran": [100, 100, 68, 0, 0, 0],
        "dev":    [100, 58, 0, 0, 0, 0],
        "sneha":  [100, 100, 100, 100, 35, 0],
    }
    cp_id = 1
    for learner in tenant_a_learners:
        for idx, course_id in enumerate(tenant_a_courses):
            pct = progress_map[learner][idx]
            if pct == 0:
                continue
            status = "completed" if pct == 100 else "in_progress"
            completed_at = YESTERDAY if pct == 100 else None
            started_at = LAST_WEEK
            session.execute(text("""
                INSERT INTO course_progress (
                    id, user_id, course_id, status, completion_percentage,
                    time_spent_seconds, started_at, completed_at, org_id, created_at
                ) VALUES (
                    :id, :uid, :cid, :status, :pct,
                    :time, :started, :completed, 1, :now
                )
            """), {
                "id": cp_id, "uid": learner, "cid": course_id, "status": status,
                "pct": pct, "time": pct * 60, "started": started_at,
                "completed": completed_at, "now": NOW,
            })
            cp_id += 1

    session.execute(text(f"SELECT setval('course_progress_id_seq', {cp_id + 10})"))

    # ── 12. Learner Events ────────────────────────────────────────────────────
    print("   📈 Learner Events...")
    event_id = 1
    for learner in tenant_a_learners:
        for idx, course_id in enumerate(tenant_a_courses):
            pct = progress_map[learner][idx]
            if pct == 0:
                continue

            mod_ids = course_modules_map.get(course_id, [])
            if not mod_ids:
                continue

            # MODULE_STARTED for each module the learner has touched
            for mid in mod_ids[:max(1, int(len(mod_ids) * pct / 100))]:
                session.execute(text("""
                    INSERT INTO learner_events (id, user_id, course_id, module_id, event_type, schema_version, payload_json, created_at, org_id)
                    VALUES (:id, :uid, :cid, :mid, 'MODULE_STARTED', 'v1', :payload, :ts, 1)
                """), {"id": event_id, "uid": learner, "cid": course_id, "mid": mid,
                       "payload": json.dumps({}), "ts": LAST_WEEK + timedelta(hours=event_id)})
                event_id += 1

            # HEARTBEAT events (engagement)
            for day_offset in range(7):
                session.execute(text("""
                    INSERT INTO learner_events (id, user_id, course_id, event_type, schema_version, payload_json, created_at, org_id)
                    VALUES (:id, :uid, :cid, 'HEARTBEAT', 'v1', :payload, :ts, 1)
                """), {"id": event_id, "uid": learner, "cid": course_id,
                       "payload": json.dumps({"time_spent_seconds": 1800}),
                       "ts": NOW - timedelta(days=day_offset, hours=idx)})
                event_id += 1

            # COURSE_COMPLETED if 100%
            if pct == 100:
                session.execute(text("""
                    INSERT INTO learner_events (id, user_id, course_id, event_type, schema_version, payload_json, created_at, org_id)
                    VALUES (:id, :uid, :cid, 'COURSE_COMPLETED', 'v1', :payload, :ts, 1)
                """), {"id": event_id, "uid": learner, "cid": course_id,
                       "payload": json.dumps({"final_score": 85}),
                       "ts": YESTERDAY})
                event_id += 1

    session.execute(text(f"SELECT setval('learner_events_id_seq', {event_id + 10})"))

    # ── 13. PAL Quiz Scores ───────────────────────────────────────────────────
    print("   🏆 PAL Quiz Scores...")
    pal_id = 1
    for learner in tenant_a_learners:
        for idx, course_id in enumerate(tenant_a_courses):
            pct = progress_map[learner][idx]
            if pct < 50:
                continue
            score = 60 + (pct * 0.3)
            session.execute(text("""
                INSERT INTO pal_quiz_scores (id, enrollment_number, user_id, course_id, course_name, score, max_score, percentage, org_id, created_at)
                VALUES (:id, :enroll, :uid, :cidx, :cname, :score, 100, :pct, 1, :now)
            """), {"id": pal_id, "enroll": learner, "uid": learner, "cidx": idx + 1,
                   "cname": course_id, "score": score, "pct": score, "now": NOW})
            pal_id += 1

    session.execute(text(f"SELECT setval('pal_quiz_scores_id_seq', {pal_id + 10})"))

    # ── 14. Tasks ─────────────────────────────────────────────────────────────
    print("   ✅ Tasks...")
    tasks = [
        ("task-1", "Review Frontend Submissions", "Review all learner project submissions for Frontend Basics", "Anika Kapoor", "ca_tenanta", "tenanta", "pending", 1),
        ("task-2", "Grade PostgreSQL Quizzes", "Grade pending quiz submissions for PostgreSQL course", "Anika Kapoor", "ca_tenanta", "tenanta", "in_progress", 1),
        ("task-3", "Plan Advanced Backend Content", "Draft syllabus for the Advanced Backend course modules", "All Faculty", None, "tenanta", "pending", 1),
    ]
    for tid, title, desc, label, assigned_to, cat_slug, status, org_id in tasks:
        session.execute(text("""
            INSERT INTO tasks (id, title, description, assigned_label, assigned_to_user_id, category_slug, status, org_id, created_at)
            VALUES (:id, :title, :desc, :label, :assigned_to, :cat_slug, :status, :org_id, :now)
        """), {"id": tid, "title": title, "desc": desc, "label": label,
               "assigned_to": assigned_to, "cat_slug": cat_slug, "status": status,
               "org_id": org_id, "now": NOW})

    # ── 15. Audit Log ─────────────────────────────────────────────────────────
    print("   📝 Audit Log...")
    audits = [
        ("ca_tenanta", "Anika Kapoor", "COURSE_PUBLISHED", "course", "course-frontend-basics", "Published Frontend Basics v1"),
        ("superadmin", "Rajan Mehra", "USER_CREATED", "user", "rahul", "Created learner account for Rahul Singh"),
        ("ca_tenanta", "Anika Kapoor", "ENROLLMENT_APPROVED", "enrollment", "neha", "Approved enrollment for Neha Pillai"),
    ]
    al_id = 1
    for actor_uid, actor_name, action, target_type, target_id, message in audits:
        session.execute(text("""
            INSERT INTO audit_log (id, actor_user_id, actor_name, action, target_type, target_id, message, org_id, created_at)
            VALUES (:id, :actor_uid, :actor_name, :action, :tt, :tid, :msg, 1, :now)
        """), {"id": al_id, "actor_uid": actor_uid, "actor_name": actor_name,
               "action": action, "tt": target_type, "tid": target_id, "msg": message, "now": NOW})
        al_id += 1

    session.execute(text(f"SELECT setval('audit_log_id_seq', {al_id + 10})"))

    # ── 16. Notifications ─────────────────────────────────────────────────────
    print("   🔔 Notifications...")
    notifs = [
        ("ca_tenanta", "New Enrollment", "Rahul Singh has enrolled in Frontend Basics.", "info"),
        ("rahul", "Course Completed!", "Congratulations! You completed Frontend Basics.", "success"),
        ("ca_tenanta", "Quiz Grading Pending", "3 quiz submissions await grading.", "warning"),
    ]
    notif_id = 1
    for uid, title, body, ntype in notifs:
        session.execute(text("""
            INSERT INTO notifications (id, user_id, title, body, type, is_read, org_id, created_at)
            VALUES (:id, :uid, :title, :body, :type, false, 1, :now)
        """), {"id": notif_id, "uid": uid, "title": title, "body": body, "type": ntype, "now": NOW})
        notif_id += 1

    session.execute(text(f"SELECT setval('notifications_id_seq', {notif_id + 10})"))

    # ── 17. Enrollment Requests ───────────────────────────────────────────────
    print("   📋 Enrollment Requests...")
    enrollments = [
        ("enr-1", "Amit Patel", "amit@telite.io", "tenanta", "self", "pending"),
        ("enr-2", "Meera Joshi", "meera@telite.io", "tenanta", "self", "approved"),
        ("enr-3", "Karan Thakur", "karan@telite.io", "tenanta", "manual", "rejected"),
    ]
    for eid, fname, email, cat_slug, req_type, status in enrollments:
        session.execute(text("""
            INSERT INTO enrollment_requests (id, full_name, email, category_slug, request_type, status, requested_at, org_id, created_at)
            VALUES (:id, :fname, :email, :cat_slug, :req_type, :status, :req_at, 1, :now)
        """), {"id": eid, "fname": fname, "email": email, "cat_slug": cat_slug,
               "req_type": req_type, "status": status,
               "req_at": NOW.strftime("%Y-%m-%dT%H:%M:%S"), "now": NOW})

    session.commit()
    print("\n✅ Seeding complete!\n")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 3: VERIFY
# ══════════════════════════════════════════════════════════════════════════════

def verify(session: Session):
    print("🔍 Verification:")
    checks = [
        ("organizations", "SELECT COUNT(*) FROM organizations"),
        ("organization_branding", "SELECT COUNT(*) FROM organization_branding"),
        ("users", "SELECT COUNT(*) FROM users"),
        ("memberships", "SELECT COUNT(*) FROM memberships"),
        ("categories", "SELECT COUNT(*) FROM categories"),
        ("courses", "SELECT COUNT(*) FROM courses"),
        ("course_sections", "SELECT COUNT(*) FROM course_sections"),
        ("course_modules", "SELECT COUNT(*) FROM course_modules"),
        ("lesson_blocks", "SELECT COUNT(*) FROM lesson_blocks"),
        ("course_versions", "SELECT COUNT(*) FROM course_versions"),
        ("course_progress", "SELECT COUNT(*) FROM course_progress"),
        ("learner_events", "SELECT COUNT(*) FROM learner_events"),
        ("pal_quiz_scores", "SELECT COUNT(*) FROM pal_quiz_scores"),
        ("tasks", "SELECT COUNT(*) FROM tasks"),
        ("audit_log", "SELECT COUNT(*) FROM audit_log"),
        ("notifications", "SELECT COUNT(*) FROM notifications"),
        ("enrollment_requests", "SELECT COUNT(*) FROM enrollment_requests"),
    ]
    for label, query in checks:
        count = session.execute(text(query)).scalar()
        status = "✅" if count > 0 else "⚠️"
        print(f"   {status} {label}: {count}")

    # Verify critical fields
    org_slug = session.execute(text("SELECT slug FROM organizations WHERE id = 1")).scalar()
    print(f"\n   🔑 Org 1 slug: '{org_slug}' (should be 'tenanta')")

    cat_slug = session.execute(text("SELECT slug FROM categories WHERE org_id = 1 LIMIT 1")).scalar()
    print(f"   🔑 Category slug: '{cat_slug}' (should be 'tenanta')")

    branding = session.execute(text("SELECT primary_color FROM organization_branding WHERE organization_id = 1")).scalar()
    print(f"   🔑 Branding primary_color: '{branding}' (should be '#2563EB')")

    block_count = session.execute(text("SELECT COUNT(*) FROM lesson_blocks")).scalar()
    print(f"   🔑 Lesson blocks: {block_count} (should be > 0)")

    ver_count = session.execute(text("SELECT COUNT(*) FROM course_versions")).scalar()
    print(f"   🔑 Course versions: {ver_count} (should be > 0)")

    print()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    with Session(engine) as session:
        delete_all(session)
        seed_all(session)
        verify(session)

    print("🎉 Done! Restart uvicorn and verify at http://localhost:3000")
