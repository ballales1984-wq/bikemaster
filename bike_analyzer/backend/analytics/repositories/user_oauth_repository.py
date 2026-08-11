"""User OAuth repository - data access abstraction for user OAuth credentials."""

from __future__ import annotations


class UserOAuthRepository:
    @staticmethod
    def get_all_user_oauth_credentials(user_id: int):
        from ...db.database import get_all_user_oauth_credentials

        return get_all_user_oauth_credentials(user_id)

    @staticmethod
    def save_user_oauth_credentials(user_id: int, provider: str, data: dict):
        from ...db.database import save_user_oauth_credentials

        return save_user_oauth_credentials(user_id, provider, data)

    @staticmethod
    def delete_user_oauth_credentials(user_id: int, provider: str):
        from ...db.database import delete_user_oauth_credentials

        return delete_user_oauth_credentials(user_id, provider)
