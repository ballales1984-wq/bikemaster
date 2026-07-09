"""Shared utilities for API routes and app factory."""


def _forwarded_value(header_value: str | None) -> str:
    if not header_value:
        return ""
    return header_value.split(",", 1)[0].strip()
