"""Date/time utilities for BikeMaster."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(value: str) -> datetime:
    if not value:
        return now_utc()
    return datetime.fromisoformat(value)


def date_only(value: Optional[str] = None) -> str:
    if value:
        return value[:10]
    return now_utc().strftime("%Y-%m-%d")


def range_for_month(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def add_days(base: str, days: int) -> str:
    dt = parse_iso(base)
    dt = dt + timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


def month_label(year: int, month: int) -> str:
    from locale import LC_TIME, setlocale
    try:
        setlocale(LC_TIME, "it_IT.UTF-8")
    except Exception:
        try:
            setlocale(LC_TIME, "Italian_Italy.1252")
        except Exception:
            pass
    d = date(year, month, 1)
    return d.strftime("%B %Y").capitalize()
