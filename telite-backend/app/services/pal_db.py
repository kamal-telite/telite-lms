# telite-backend/pal_db.py
# Phase 4 — PAL SQLite database
# Stores quiz scores, weak topics, recommendations
# No extra install needed — sqlite3 is built into Python

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pal_data.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn


def init_db():
    """Create all tables if they don't exist. Called at startup."""
    conn = get_conn()
    c = conn.cursor()

    # ── Quiz scores ───────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_number TEXT    NOT NULL,
            course_id         INTEGER NOT NULL,
            course_name       TEXT,
            quiz_id           INTEGER,
            quiz_name         TEXT,
            topic             TEXT,
            score             REAL    NOT NULL,   -- 0 to 100
            max_score         REAL    NOT NULL DEFAULT 100,
            percentage        REAL    GENERATED ALWAYS AS
                                (ROUND(score * 100.0 / max_score, 2)) STORED,
            branch            TEXT,
            college           TEXT,
            synced_from_moodle INTEGER DEFAULT 0,  -- 1 if pulled from Moodle API
            created_at        TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── PAL recommendations ───────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_number TEXT    NOT NULL,
            level             TEXT    NOT NULL,   -- remedial / normal / advanced
            weak_topics       TEXT,               -- JSON array as string
            strong_topics     TEXT,               -- JSON array as string
            recommended_courses TEXT,             -- JSON array as string
            recommended_resources TEXT,           -- JSON array as string
            avg_score         REAL,
            email_sent        INTEGER DEFAULT 0,
            generated_at      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Topic performance (aggregated) ────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS topic_performance (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_number TEXT    NOT NULL,
            topic             TEXT    NOT NULL,
            avg_score         REAL,
            attempts          INTEGER DEFAULT 1,
            last_updated      TEXT    DEFAULT (datetime('now')),
            UNIQUE(enrollment_number, topic)
        )
    """)

    conn.commit()
    conn.close()
    print("[PAL DB] Initialised at", DB_PATH)


# ── Score operations ──────────────────────────────────────────────────────
def insert_score(enrollment: str, course_id: int, course_name: str,
                 quiz_id: int, quiz_name: str, topic: str,
                 score: float, max_score: float = 100,
                 branch: str = "", college: str = "",
                 synced: bool = False) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO quiz_scores
            (enrollment_number, course_id, course_name, quiz_id, quiz_name,
             topic, score, max_score, branch, college, synced_from_moodle)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (enrollment, course_id, course_name, quiz_id, quiz_name,
          topic, score, max_score, branch, college, int(synced)))

    # Update topic performance aggregate
    pct = round(score * 100.0 / max_score, 2)
    c.execute("""
        INSERT INTO topic_performance (enrollment_number, topic, avg_score, attempts)
        VALUES (?,?,?,1)
        ON CONFLICT(enrollment_number, topic) DO UPDATE SET
            avg_score    = ROUND((avg_score * attempts + excluded.avg_score) / (attempts + 1), 2),
            attempts     = attempts + 1,
            last_updated = datetime('now')
    """, (enrollment, topic, pct))

    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def get_scores(enrollment: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM quiz_scores
        WHERE enrollment_number = ?
        ORDER BY created_at DESC
    """, (enrollment,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_avg_score(enrollment: str) -> float | None:
    conn = get_conn()
    row = conn.execute("""
        SELECT ROUND(AVG(percentage), 2) as avg
        FROM quiz_scores WHERE enrollment_number = ?
    """, (enrollment,)).fetchone()
    conn.close()
    return row["avg"] if row and row["avg"] is not None else None


def get_topic_performance(enrollment: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM topic_performance
        WHERE enrollment_number = ?
        ORDER BY avg_score ASC
    """, (enrollment,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_weak_topics(enrollment: str, threshold: float = 60.0) -> list[str]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT topic FROM topic_performance
        WHERE enrollment_number = ? AND avg_score < ?
        ORDER BY avg_score ASC
    """, (enrollment, threshold)).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def get_strong_topics(enrollment: str, threshold: float = 75.0) -> list[str]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT topic FROM topic_performance
        WHERE enrollment_number = ? AND avg_score >= ?
        ORDER BY avg_score DESC
    """, (enrollment, threshold)).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def save_recommendation(enrollment: str, level: str, weak_topics: list,
                        strong_topics: list, courses: list,
                        resources: list, avg_score: float) -> int:
    import json
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO recommendations
            (enrollment_number, level, weak_topics, strong_topics,
             recommended_courses, recommended_resources, avg_score)
        VALUES (?,?,?,?,?,?,?)
    """, (enrollment, level,
          json.dumps(weak_topics), json.dumps(strong_topics),
          json.dumps(courses), json.dumps(resources), avg_score))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def mark_email_sent(recommendation_id: int):
    conn = get_conn()
    conn.execute("UPDATE recommendations SET email_sent=1 WHERE id=?", (recommendation_id,))
    conn.commit()
    conn.close()


def get_all_students_summary() -> list[dict]:
    """For admin dashboard — all students with their avg score and level."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            enrollment_number,
            ROUND(AVG(percentage), 2) as avg_score,
            COUNT(*) as total_quizzes,
            MAX(created_at) as last_activity
        FROM quiz_scores
        GROUP BY enrollment_number
        ORDER BY avg_score ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
