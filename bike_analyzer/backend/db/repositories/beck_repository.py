"""Beck repository — SQLite persistence for Beck Depression Inventory assessments."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


def _beck_severity(total_score: int) -> str:
    if total_score <= 13:
        return "minimal"
    if total_score <= 19:
        return "mild"
    if total_score <= 28:
        return "moderate"
    return "severe"


@pg_dispatch("bike_analyzer.backend.db.postgres_beck")
def save_beck_assessment(assessment: dict, tenant_id: int = 0) -> int:
    now = datetime.now(UTC).isoformat()
    answers = assessment.get("answers", [])
    total_score = int(sum(int(score) for _, score in answers)) if answers else 0
    severity = _beck_severity(total_score)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO beck_assessments
            (athlete_id, tenant_id, total_score, severity, answers, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                assessment.get("athlete_id"),
                assessment.get("tenant_id", tenant_id),
                total_score,
                severity,
                json.dumps(answers),
                assessment.get("notes"),
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_beck")
def get_beck_assessment(assessment_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM beck_assessments WHERE id = ?", (assessment_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "total_score": row["total_score"],
            "severity": row["severity"],
            "answers": json.loads(row["answers"]) if row["answers"] else [],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_beck")
def get_beck_assessments_by_athlete(athlete_id: int, tenant_id: int = 0, limit: int = 100) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM beck_assessments
            WHERE athlete_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            LIMIT ?""",
            (athlete_id, tenant_id, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "athlete_id": r["athlete_id"],
                "tenant_id": r["tenant_id"],
                "total_score": r["total_score"],
                "severity": r["severity"],
                "answers": json.loads(r["answers"]) if r["answers"] else [],
                "notes": r["notes"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]


@pg_dispatch("bike_analyzer.backend.db.postgres_beck")
def get_latest_beck_assessment(athlete_id: int, tenant_id: int = 0) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM beck_assessments
            WHERE athlete_id = ? AND tenant_id = ?
            ORDER BY created_at DESC
            LIMIT 1""",
            (athlete_id, tenant_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "athlete_id": row["athlete_id"],
            "tenant_id": row["tenant_id"],
            "total_score": row["total_score"],
            "severity": row["severity"],
            "answers": json.loads(row["answers"]) if row["answers"] else [],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
