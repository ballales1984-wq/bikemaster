"""PostgreSQL-backed persistence for Beck assessments."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_beck_assessments_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS beck_assessments (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                total_score INTEGER NOT NULL DEFAULT 0,
                severity TEXT NOT NULL DEFAULT 'minimal',
                answers JSONB DEFAULT '[]'::jsonb,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT NOW(),
                updated_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()


def _beck_severity(total_score: int) -> str:
    if total_score <= 13:
        return "minimal"
    if total_score <= 19:
        return "mild"
    if total_score <= 28:
        return "moderate"
    return "severe"


def save_beck_assessment(assessment: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_beck_assessments_table(conn)
        now = datetime.now(UTC).isoformat()
        answers = assessment.get("answers", [])
        total_score = int(sum(int(score) for _, score in answers)) if answers else 0
        severity = _beck_severity(total_score)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO beck_assessments
                (athlete_id, tenant_id, total_score, severity, answers, notes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
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
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_beck_assessment(assessment_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_beck_assessments_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM beck_assessments WHERE id = %s", (assessment_id,))
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
    finally:
        _safe_close(conn)


def get_beck_assessments_by_athlete(athlete_id: int, tenant_id: int = 0, limit: int = 100) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_beck_assessments_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM beck_assessments
                WHERE athlete_id = %s AND tenant_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
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
    finally:
        _safe_close(conn)


def get_latest_beck_assessment(athlete_id: int, tenant_id: int = 0) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_beck_assessments_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM beck_assessments
                WHERE athlete_id = %s AND tenant_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
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
    finally:
        _safe_close(conn)
