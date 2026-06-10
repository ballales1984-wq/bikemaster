"""Date/time utilities for BikeMaster."""

from __future__ import annotations

import contextlib
from datetime import UTC, date, datetime, timedelta


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime | None = None) -> str:
    if dt is None:
        dt = now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def parse_iso(value: str) -> datetime:
    if not value:
        return now_utc()
    return datetime.fromisoformat(value)


def date_only(value: str | None = None) -> str:
    if value:
        return value[:10]
    return now_utc().strftime("%Y-%m-%d")


def range_for_month(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
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
        with contextlib.suppress(Exception):
            setlocale(LC_TIME, "Italian_Italy.1252")
    d = date(year, month, 1)
    return d.strftime("%B %Y").capitalize()
