"""Google OAuth2 authentication integration."""

from __future__ import annotations

import urllib.parse


def get_google_oauth_url(
    client_id: str,
    redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback",
    state: str = "",
) -> str:
    """Generate Google OAuth2 authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_google_code(
    client_id: str, client_secret: str, code: str, redirect_uri: str
) -> dict:
    """Exchange authorization code for token."""
    import requests

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_google_user_info(access_token: str) -> dict:
    """Fetch user info from Google."""
    import requests

    resp = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def create_google_session(user_info: dict, athlete_data: dict | None = None) -> dict:
    """Create session data from Google user info."""
    from ..security import create_access_token

    return {
        "access_token": create_access_token(
            subject=user_info.get("sub", ""),
            is_admin=False,
        ),
        "token_type": "bearer",
        "user_id": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
    }