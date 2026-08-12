"""Performance repository - data access for power metrics and FTP history."""

from __future__ import annotations

from datetime import UTC, datetime

from ...db.database import get_db_connection


class PerformanceRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def save_performance_metrics(
        athlete_id: int,
        ride_id: int,
        date: str,
        average_power: float | None,
        normalized_power: float | None,
        intensity_factor: float | None,
        tss: float | None,
        ftp_watts: float | None,
        tenant_id: int = 0,
    ) -> None:
        """UPSERT performance metrics for a ride."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM performance_metrics WHERE athlete_id = ? AND ride_id = ?",
                (athlete_id, ride_id),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """UPDATE performance_metrics
                       SET normalized_power = ?, intensity_factor = ?, tss = ?,
                           average_power = ?, ftp_watts = ?, created_at = ?
                       WHERE id = ?""",
                    (
                        normalized_power,
                        intensity_factor,
                        tss,
                        average_power,
                        ftp_watts,
                        PerformanceRepository._now_iso(),
                        existing[0],
                    ),
                )
            else:
                cur.execute(
                    """INSERT INTO performance_metrics
                       (athlete_id, tenant_id, ride_id, date, average_power,
                        normalized_power, intensity_factor, tss, ftp_watts, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        athlete_id,
                        tenant_id,
                        ride_id,
                        date,
                        average_power,
                        normalized_power,
                        intensity_factor,
                        tss,
                        ftp_watts,
                        PerformanceRepository._now_iso(),
                    ),
                )
            conn.commit()

    @staticmethod
    def record_ftp(
        athlete_id: int,
        ftp_watts: float,
        date: str | None = None,
        source: str = "test",
        note: str | None = None,
        tenant_id: int = 0,
    ) -> dict:
        """Registra un valore FTP in ftp_history (UPSERT per athlete+date)."""
        if date is None:
            date = PerformanceRepository._now_iso()[:10]

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM ftp_history WHERE athlete_id = ? AND date = ?",
                (athlete_id, date),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """UPDATE ftp_history SET ftp_watts = ?, source = ?, note = ?,
                       created_at = ? WHERE id = ?""",
                    (ftp_watts, source, note, PerformanceRepository._now_iso(), existing[0]),
                )
                record_id = existing[0]
            else:
                cur.execute(
                    """INSERT INTO ftp_history
                       (athlete_id, tenant_id, date, ftp_watts, source, note, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (athlete_id, tenant_id, date, ftp_watts, source, note, PerformanceRepository._now_iso()),
                )
                record_id = cur.lastrowid
            conn.commit()
        return {
            "id": record_id,
            "athlete_id": athlete_id,
            "tenant_id": tenant_id,
            "date": date,
            "ftp_watts": ftp_watts,
            "source": source,
            "note": note,
        }

    @staticmethod
    def get_ftp_history(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
        """Restituisce lo storico FTP di un atleta ordinato per data crescente."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            if tenant_id is not None:
                cur.execute(
                    "SELECT id, athlete_id, tenant_id, date, ftp_watts, source, note, created_at "
                    "FROM ftp_history WHERE athlete_id = ? AND tenant_id = ? ORDER BY date ASC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT id, athlete_id, tenant_id, date, ftp_watts, source, note, created_at "
                    "FROM ftp_history WHERE athlete_id = ? ORDER BY date ASC",
                    (athlete_id,),
                )
            rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "athlete_id": r[1],
                "tenant_id": r[2],
                "date": r[3],
                "ftp_watts": r[4],
                "source": r[5],
                "note": r[6],
                "created_at": r[7],
            }
            for r in rows
        ]

    @staticmethod
    def get_performance_metrics(
        athlete_id: int,
        tenant_id: int | None = None,
        ride_id: int | None = None,
    ) -> list[dict]:
        """Restituisce le metriche di potenza persistite per un atleta (opz. per ride)."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            if ride_id is not None:
                cur.execute(
                    "SELECT * FROM performance_metrics WHERE athlete_id = ? AND ride_id = ? "
                    "ORDER BY date ASC",
                    (athlete_id, ride_id),
                )
            elif tenant_id is not None:
                cur.execute(
                    "SELECT * FROM performance_metrics WHERE athlete_id = ? AND tenant_id = ? "
                    "ORDER BY date ASC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM performance_metrics WHERE athlete_id = ? ORDER BY date ASC",
                    (athlete_id,),
                )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d.pop("tenant_id", None)
            result.append(d)
        return result
