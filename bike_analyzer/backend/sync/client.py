"""HTTP client for cloud sync API communication.

Wraps the cloud sync endpoints defined in the deployment plan §3.2:
  GET  /sync/check
  POST /sync/push
  GET  /sync/pull

Uses the existing ``http_async.request_json`` helper with exponential backoff.
All errors are caught and returned as error dicts — cloud unavailability must
never break local operation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..http_async import request_json
from ..utils.logger import get_logger
from .models import ChangeDelta, SyncCheckResult, SyncPushResult

logger = get_logger(__name__)


class SyncClientError(Exception):
    """Raised when the cloud sync API returns a non-retryable error."""


class SyncClient:
    """Client for the BikeMaster cloud sync API."""

    def __init__(self, base_url: str, auth_token: str = "", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def check(self, last_sync_ts: str | None = None) -> SyncCheckResult | dict[str, Any]:
        """Call GET /sync/check to discover server changes."""
        params: dict[str, Any] = {}
        if last_sync_ts:
            params["since"] = last_sync_ts
        try:
            data = await request_json(
                "GET",
                f"{self.base_url}/sync/check",
                params=params,
                headers=self._headers,
                timeout=self.timeout,
            )
            if isinstance(data, dict):
                return SyncCheckResult(
                    last_sync_ts=data.get("last_sync_ts"),
                    server_changes_count=int(data.get("server_changes_count", 0)),
                    server_changes=list(data.get("server_changes", [])),
                    server_version=data.get("server_version"),
                )
            return data
        except Exception as exc:
            logger.debug("Sync check failed: %s", exc)
            return {"error": str(exc)}

    async def push(self, deltas: list[ChangeDelta]) -> SyncPushResult | dict[str, Any]:
        """Call POST /sync/push to send local deltas."""
        payload = {
            "deltas": [d.to_dict() for d in deltas],
        }
        try:
            data = await request_json(
                "POST",
                f"{self.base_url}/sync/push",
                json=payload,
                headers=self._headers,
                timeout=self.timeout,
            )
            if isinstance(data, dict):
                conflicts = []
                for c_data in data.get("conflicts", []):
                    from ..sync.conflict_resolver import ConflictRecord

                    conflicts.append(
                        ConflictRecord(
                            entity_type=c_data.get("entity_type", ""),
                            entity_id=int(c_data.get("entity_id", 0)),
                            local_data=c_data.get("local_data", {}),
                            remote_data=c_data.get("remote_data", {}),
                            local_reliability=float(c_data.get("local_reliability", 1.0)),
                            remote_reliability=float(c_data.get("remote_reliability", 1.0)),
                            local_modified=c_data.get("local_modified", ""),
                            remote_modified=c_data.get("remote_modified", ""),
                        )
                    )
                return SyncPushResult(
                    accepted=int(data.get("accepted", 0)),
                    conflicts=conflicts,
                    errors=list(data.get("errors", [])),
                )
            return data
        except Exception as exc:
            logger.debug("Sync push failed: %s", exc)
            return {"error": str(exc)}

    async def pull(self, since: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        """Call GET /sync/pull to receive remote changes."""
        params: dict[str, Any] = {}
        if since:
            params["since"] = since
        try:
            data = await request_json(
                "GET",
                f"{self.base_url}/sync/pull",
                params=params,
                headers=self._headers,
                timeout=self.timeout,
            )
            if isinstance(data, dict) and "changes" in data:
                return list(data["changes"])
            if isinstance(data, list):
                return data
            return data
        except Exception as exc:
            logger.debug("Sync pull failed: %s", exc)
            return {"error": str(exc)}

    async def health(self) -> dict[str, Any]:
        """Quick health check on the sync endpoint."""
        try:
            data = await request_json(
                "GET",
                f"{self.base_url}/health",
                headers=self._headers,
                timeout=10.0,
            )
            return data if isinstance(data, dict) else {"status": "ok"}
        except Exception as exc:
            logger.debug("Sync health check failed: %s", exc)
            return {"status": "error", "error": str(exc)}


__all__ = ["SyncClient", "SyncClientError"]
