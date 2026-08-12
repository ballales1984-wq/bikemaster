"""Auth and user OAuth credentials routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...security import create_access_token, create_refresh_token, get_current_user, save_refresh_token

router = APIRouter()


class UserOAuthCredentials(BaseModel):
    provider: str
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None


@router.post("/auth/switch-athlete/{athlete_id}")
async def switch_athlete(athlete_id: int, current_user: dict = Depends(get_current_user)):
    """Switch the active athlete profile and return a new JWT with athlete_id claim."""
    from ...analytics.repositories.athlete_repository import AthleteRepository

    user_id = int(current_user["id"])
    athlete = AthleteRepository().get_by_id(athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    if athlete.get("user_id") != user_id and athlete_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this athlete")

    access_token = create_access_token(
        subject=str(user_id),
        is_admin=current_user.get("is_admin", False),
        tenant_id=current_user.get("tenant_id", user_id),
        is_client=current_user.get("is_client", False),
        athlete_id=athlete_id,
    )
    refresh_token = create_refresh_token(
        subject=str(user_id),
        is_admin=current_user.get("is_admin", False),
        tenant_id=current_user.get("tenant_id", user_id),
        is_client=current_user.get("is_client", False),
    )
    save_refresh_token(user_id, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user_id,
        "athlete_id": athlete_id,
    }


@router.get("/connections/credentials")
async def list_my_oauth_credentials(current_user: dict = Depends(get_current_user)):
    """List OAuth credentials configured for the current user (without secrets)."""
    from ...analytics.repositories.user_oauth_repository import UserOAuthRepository

    user_id = int(current_user["id"])
    creds = UserOAuthRepository.get_all_user_oauth_credentials(user_id)
    result = []
    for c in creds:
        result.append({
            "id": c["id"],
            "provider": c["provider"],
            "client_id": c["client_id"],
            "redirect_uri": c["redirect_uri"],
            "scope": c["scope"],
            "has_secret": bool(c["client_secret"]),
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
        })
    return {"credentials": result}


@router.post("/connections/credentials")
async def set_my_oauth_credentials(credentials: UserOAuthCredentials, current_user: dict = Depends(get_current_user)):
    """Set or update OAuth credentials for a specific provider."""
    from ...analytics.repositories.user_oauth_repository import UserOAuthRepository

    user_id = int(current_user["id"])
    data = credentials.model_dump(exclude_unset=True)
    if not data.get("client_id") and not data.get("client_secret"):
        raise HTTPException(status_code=400, detail="client_id or client_secret required")
    UserOAuthRepository.save_user_oauth_credentials(user_id, credentials.provider, data)
    return {"status": "saved", "provider": credentials.provider}


@router.delete("/connections/credentials/{provider}")
async def delete_my_oauth_credentials(provider: str, current_user: dict = Depends(get_current_user)):
    """Delete OAuth credentials for a specific provider."""
    from ...analytics.repositories.user_oauth_repository import UserOAuthRepository

    user_id = int(current_user["id"])
    ok = UserOAuthRepository.delete_user_oauth_credentials(user_id, provider)
    if not ok:
        raise HTTPException(status_code=404, detail="Credentials not found")
    return {"status": "deleted", "provider": provider}
