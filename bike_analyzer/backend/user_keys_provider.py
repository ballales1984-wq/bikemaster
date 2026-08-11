"""User API keys provider abstraction.

Allows service layers to resolve user-provided API keys without importing
the HTTP-scoped ``request_context`` module directly. The default
implementation reads from the request-scoped ``ContextVar``; tests and other
callers can inject an alternative provider.
"""

from __future__ import annotations

from typing import Protocol


class UserKeysProvider(Protocol):
    def get_keys(self) -> dict[str, str]: ...


class ContextVarUserKeysProvider:
    def get_keys(self) -> dict[str, str]:
        from .request_context import get_request_user_keys

        return get_request_user_keys()
