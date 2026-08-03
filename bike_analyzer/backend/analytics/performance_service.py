"""Performance analytics service: calcola e persiste metriche di potenza e FTP.

Funzioni di alto livello che leggono le ride (con stream di potenza dai GPS point),
calcolano NP/IF/TSS via ``analytics.performance`` e scrivono su
``performance_metrics`` / ``ftp_history`` (layer DB SQLite in ``db.database``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..db.database import get_db_connection
from .performance import (
    calculate_power_metrics_with_error,
    estimate_ftp_from_ride,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _power_stream_from_ride(ride: dict) -> list[float]:
    """Estrae lo stream di potenza (W) dai gps_points della ride, se presenti."""
    gps = ride.get("gps_points")
    if not gps:
        return []
    return [float(p["power"]) for p in gps if p.get("power") is not None]


def _duration_seconds(ride: dict) -> float | None:
    duration_min = ride.get("duration_minutes")
    if duration_min:
        return float(duration_min) * 60.0
    return None


def compute_ride_power_metrics(ride: dict, ftp: float | None) -> dict:
    """Calcola le metriche di potenza per una ride senza persistere.

    Ritorna il dict ``calculate_power_metrics`` arricchito di ``ride_id``/``date``
    e margini di errore per ogni metrica.
    """
    power_stream = _power_stream_from_ride(ride)
    duration = _duration_seconds(ride)
    metrics = calculate_power_metrics_with_error(power_stream, ftp, duration)
    result = {
        "ride_id": ride.get("id"),
        "date": ride.get("date"),
    }
    for key, ev in metrics.items():
        if ev is not None:
            result[key] = ev.value
            result[f"{key}_error"] = ev.to_dict()
        else:
            result[key] = None
    return result


def save_ride_performance(
    athlete_id: int,
    ride: dict,
    ftp: float | None = None,
    tenant_id: int = 0,
) -> dict | None:
    """Calcola e persiste le metriche di potenza di una ride.

    Scrive su ``performance_metrics`` (UPSERT per athlete+ride) e ritorna il dict
    calcolato arricchito di margini di errore. Se lo stream di potenza e' assente
    ritorna None (niente da calcolare).
    """
    power_stream = _power_stream_from_ride(ride)
    if not power_stream:
        return None

    duration = _duration_seconds(ride)
    metrics = calculate_power_metrics_with_error(power_stream, ftp, duration)
    ride_id = ride.get("id")
    date = ride.get("date") or _now_iso()[:10]
    owner_athlete_id = ride.get("athlete_id") or athlete_id

    result = {
        "ride_id": ride_id,
        "date": date,
        "average_power": metrics["average_power"].value if metrics["average_power"] else None,
        "normalized_power": metrics["normalized_power"].value if metrics["normalized_power"] else None,
        "intensity_factor": metrics["intensity_factor"].value if metrics["intensity_factor"] else None,
        "tss": metrics["tss"].value if metrics["tss"] else None,
    }
    for key, ev in metrics.items():
        if ev is not None:
            result[f"{key}_error"] = ev.to_dict()

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
                    result["normalized_power"],
                    result["intensity_factor"],
                    result["tss"],
                    result["average_power"],
                    ftp,
                    _now_iso(),
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
                    owner_athlete_id,
                    tenant_id,
                    ride_id,
                    date,
                    result["average_power"],
                    result["normalized_power"],
                    result["intensity_factor"],
                    result["tss"],
                    ftp,
                    _now_iso(),
                ),
            )
        conn.commit()
    return result


def record_ftp(
    athlete_id: int,
    ftp_watts: float,
    date: str | None = None,
    source: str = "test",
    note: str | None = None,
    tenant_id: int = 0,
) -> dict:
    """Registra un valore FTP in ``ftp_history`` (UPSERT per athlete+date).

    Ritorna il record salvato. ``date`` default = oggi (UTC, YYYY-MM-DD).
    """
    if date is None:
        date = _now_iso()[:10]
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
                (ftp_watts, source, note, _now_iso(), existing[0]),
            )
            record_id = existing[0]
        else:
            cur.execute(
                """INSERT INTO ftp_history
                   (athlete_id, tenant_id, date, ftp_watts, source, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (athlete_id, tenant_id, date, ftp_watts, source, note, _now_iso()),
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


def get_latest_ftp(athlete_id: int, tenant_id: int | None = None) -> float | None:
    """Ritorna l'ultimo FTP noto dell'atleta (per data) o None."""
    history = get_ftp_history(athlete_id, tenant_id)
    return history[-1]["ftp_watts"] if history else None


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


def recompute_athlete_performance(
    athlete_id: int,
    rides: list[dict],
    ftp: float | None = None,
    tenant_id: int = 0,
) -> list[dict]:
    """Ricalcola e persiste le metriche di potenza per tutte le ride di un atleta.

    Se ``ftp`` e' None, prova a stimarlo dalla ride piu' lunga disponibile.
    Ritorna la lista dei dict metrica salvati.
    """
    if ftp is None:
        best = None
        best_dur = -1
        for ride in rides:
            stream = _power_stream_from_ride(ride)
            dur = _duration_seconds(ride) or 0
            if stream and dur > best_dur:
                best, best_dur = ride, dur
        if best is not None:
            ftp = estimate_ftp_from_ride(_power_stream_from_ride(best), best_dur)

    saved = []
    for ride in rides:
        m = save_ride_performance(athlete_id, ride, ftp, tenant_id)
        if m:
            saved.append(m)
    return saved


__all__ = [
    "compute_ride_power_metrics",
    "save_ride_performance",
    "record_ftp",
    "get_ftp_history",
    "get_latest_ftp",
    "get_performance_metrics",
    "recompute_athlete_performance",
]
