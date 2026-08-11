"""User OAuth repository - data access abstraction for user OAuth credentials."""

from __future__ import annotations

from ...db.database import (
    delete_user_oauth_credentials,
    get_all_user_oauth_credentials,
    save_user_oauth_credentials,
)


class UserOAuthRepository:
    @staticmethod
    def get_all_user_oauth_credentials(user_id: int):
        return get_all_user_oauth_credentials(user_id)

    @staticmethod
    def save_user_oauth_credentials(user_id: int, provider: str, data: dict):
        return save_user_oauth_credentials(user_id, provider, data)

    @staticmethod
    def delete_user_oauth_credentials(user_id: int, provider: str):
        return delete_user_oauth_credentials(user_id, provider)
