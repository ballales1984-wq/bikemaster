"""Auth and user OAuth credentials routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from ...db.database import get_user_by_id, get_user_by_username, save_user
from ...security import (
    create_access_token,
    create_refresh_token,
    decode_token_with_fallback,
    get_current_user,
    hash_password,
    is_token_revoked,
    revoke_refresh_token,
    save_refresh_token,
    verify_password,
)
from ...settings import get_settings

router = APIRouter()
_s = get_settings()


class UserOAuthCredentials(BaseModel):
    provider: str
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


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


@router.post("/auth/login")
async def local_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Local login using the SQLite users table (offline/local-first mode)."""
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

    access_token = create_access_token(
        subject=str(user["id"]),
        is_admin=bool(user.get("is_admin")),
        tenant_id=user.get("tenant_id", user["id"]),
        is_client=bool(user.get("is_client")),
    )
    refresh_token = create_refresh_token(
        subject=str(user["id"]),
        is_admin=bool(user.get("is_admin")),
        tenant_id=user.get("tenant_id", user["id"]),
        is_client=bool(user.get("is_client")),
    )
    await save_refresh_token(int(user["id"]), refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user["username"],
        "id": user["id"],
        "is_admin": bool(user.get("is_admin")),
    }


@router.post("/auth/register")
async def local_register(request: Request, data: RegisterRequest):
    """Local register using the SQLite users table (offline/local-first mode)."""
    existing = get_user_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    password_hash = hash_password(data.password)
    user_id = save_user(
        {
            "username": data.username,
            "email": data.email,
            "password_hash": password_hash,
            "is_admin": False,
            "is_client": False,
            "is_active": True,
        }
    )
    return {
        "username": data.username,
        "email": data.email,
        "msg": "Utente creato",
        "is_admin": False,
        "id": user_id,
    }


@router.post("/auth/logout")
async def local_logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Local logout: revoke refresh token."""
    await revoke_refresh_token(int(current_user["id"]))
    return {"msg": "Logged out successfully"}


@router.post("/auth/refresh")
async def local_refresh(request: Request, payload: dict = Body(...)):
    """Refresh access token using a valid refresh token (SQLite/local mode)."""
    refresh_token = payload.get("refresh_token")
    jwt_payload = await decode_token_with_fallback(refresh_token)
    if not jwt_payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if jwt_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user_id = jwt_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    jti = jwt_payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    is_admin = bool(jwt_payload.get("is_admin", False))
    is_client = bool(jwt_payload.get("is_client", False))
    tenant_id = jwt_payload.get("tenant_id")
    resolved_tenant = int(tenant_id) if tenant_id is not None else int(user_id)
    return {
        "access_token": create_access_token(
            subject=str(user_id), is_admin=is_admin, tenant_id=resolved_tenant, is_client=is_client
        ),
        "token_type": "bearer",
    }


@router.get("/auth/me")
async def local_me(current_user: dict = Depends(get_current_user)):
    """Return the current user profile from the local SQLite store."""
    user = get_user_by_id(int(current_user["id"]))
    if not user:
        return {
            "id": current_user["id"],
            "username": "",
            "email": None,
            "is_admin": current_user.get("is_admin", False),
            "is_client": current_user.get("is_client", False),
            "tenant_id": current_user.get("tenant_id", current_user["id"]),
        }
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "is_admin": bool(user.get("is_admin")),
        "is_client": bool(user.get("is_client")),
        "tenant_id": user.get("tenant_id", user["id"]),
    }
