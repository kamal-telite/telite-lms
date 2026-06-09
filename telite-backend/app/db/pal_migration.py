"""
PAL SQLite → PostgreSQL Migration Utility.

PHASE 3: Migrates all data from the legacy pal_data.db SQLite database
into the new PostgreSQL pal_quiz_scores, pal_recommendations, and
pal_topic_performance tables — with org_id tenant isolation applied.

Usage:
    python -m app.db.pal_migration --org-id 1 --sqlite-path data/pal_data.db
    python -m app.db.pal_migration --org-id 1  # uses default path
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger("telite.db.pal_migration")


def _get_sqlite_conn(sqlite_path: str) -> sqlite3.Connection:
    path = Path(sqlite_path)
    if not path.exists():
        raise FileNotFoundError(f"PAL SQLite database not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def migrate_pal_to_postgres(
    org_id: int,
    sqlite_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Migrate PAL data from SQLite to PostgreSQL for a given org.

    Args:
        org_id:      Target organisation ID for all migrated rows.
        sqlite_path: Path to pal_data.db. Defaults to app/pal_data.db.
        dry_run:     If True, reads data but does not write to PostgreSQL.

    Returns:
        Dict with counts: {scores, recommendations, topics, errors}
    """
    from app.db.engine import get_db_session

    if sqlite_path is None:
        backend_dir = Path(__file__).resolve().parents[2]
        sqlite_path = str(backend_dir / "pal_data.db")

    logger.info("Starting PAL migration: org_id=%d, source=%s, dry_run=%s",
                org_id, sqlite_path, dry_run)

    counts = {"scores": 0, "recommendations": 0, "topics": 0, "errors": 0}

    try:
        sqlite_conn = _get_sqlite_conn(sqlite_path)
    except FileNotFoundError as e:
        logger.warning("PAL SQLite not found — skipping migration: %s", e)
        return counts

    with get_db_session() as pg_session:
        # ── Migrate quiz_scores ───────────────────────────────────────────────
        rows = sqlite_conn.execute("SELECT * FROM quiz_scores").fetchall()
        logger.info("Migrating %d quiz score rows…", len(rows))

        for row in rows:
            try:
                if not dry_run:
                    from app.models.pal import PalQuizScore
                    score = PalQuizScore(
                        org_id=org_id,
                        enrollment_number=row["enrollment_number"],
                        course_id=row["course_id"],
                        course_name=row["course_name"],
                        quiz_id=row["quiz_id"],
                        quiz_name=row["quiz_name"],
                        topic=row["topic"],
                        score=float(row["score"]),
                        max_score=float(row["max_score"] or 100),
                        percentage=float(row["percentage"]) if row["percentage"] else None,
                        branch=row["branch"],
                        college=row["college"],
                        synced_from_moodle=bool(row["synced_from_moodle"]),
                    )
                    pg_session.add(score)
                counts["scores"] += 1
            except Exception as exc:
                logger.error("Error migrating score row %s: %s", dict(row), exc)
                counts["errors"] += 1

        # ── Migrate recommendations ───────────────────────────────────────────
        rows = sqlite_conn.execute("SELECT * FROM recommendations").fetchall()
        logger.info("Migrating %d recommendation rows…", len(rows))

        for row in rows:
            try:
                if not dry_run:
                    from app.models.pal import PalRecommendation
                    rec = PalRecommendation(
                        org_id=org_id,
                        enrollment_number=row["enrollment_number"],
                        level=row["level"],
                        weak_topics=row["weak_topics"],
                        strong_topics=row["strong_topics"],
                        recommended_courses=row["recommended_courses"],
                        recommended_resources=row["recommended_resources"],
                        avg_score=float(row["avg_score"]) if row["avg_score"] else None,
                        email_sent=bool(row["email_sent"]),
                    )
                    pg_session.add(rec)
                counts["recommendations"] += 1
            except Exception as exc:
                logger.error("Error migrating recommendation row: %s", exc)
                counts["errors"] += 1

        # ── Migrate topic_performance ─────────────────────────────────────────
        rows = sqlite_conn.execute("SELECT * FROM topic_performance").fetchall()
        logger.info("Migrating %d topic performance rows…", len(rows))

        for row in rows:
            try:
                if not dry_run:
                    from app.models.pal import PalTopicPerformance
                    topic = PalTopicPerformance(
                        org_id=org_id,
                        enrollment_number=row["enrollment_number"],
                        topic=row["topic"],
                        avg_score=float(row["avg_score"]) if row["avg_score"] else None,
                        attempts=int(row["attempts"]),
                        last_updated=row["last_updated"],
                    )
                    pg_session.add(topic)
                counts["topics"] += 1
            except Exception as exc:
                logger.error("Error migrating topic row: %s", exc)
                counts["errors"] += 1

        if not dry_run:
            pg_session.commit()
            logger.info(
                "PAL migration complete: scores=%d, recommendations=%d, "
                "topics=%d, errors=%d",
                counts["scores"], counts["recommendations"],
                counts["topics"], counts["errors"],
            )
        else:
            logger.info(
                "DRY RUN complete (no data written): scores=%d, "
                "recommendations=%d, topics=%d",
                counts["scores"], counts["recommendations"], counts["topics"],
            )

    sqlite_conn.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Migrate PAL SQLite → PostgreSQL")
    parser.add_argument("--org-id", type=int, required=True,
                        help="Target organisation ID for migrated rows")
    parser.add_argument("--sqlite-path", type=str, default=None,
                        help="Path to pal_data.db (default: app/pal_data.db)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read data but do not write to PostgreSQL")
    args = parser.parse_args()

    result = migrate_pal_to_postgres(
        org_id=args.org_id,
        sqlite_path=args.sqlite_path,
        dry_run=args.dry_run,
    )
    print(f"\nMigration result: {result}")
