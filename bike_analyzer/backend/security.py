"""JWT authentication helpers.

Lightweight implementation using python-jose with HS256.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    SECRET_KEY,
    SECRET_KEY_PREVIOUS,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _get_pwd_context():
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")


pwd_context = _get_pwd_context()


def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        salt = SECRET_KEY[:16] if SECRET_KEY else "bikemaster_salt"
        return f"sha256${hashlib.sha256((password + salt).encode()).hexdigest()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        if hashed.startswith("sha256$"):
            salt = SECRET_KEY[:16] if SECRET_KEY else "bikemaster_salt"
            expected = hashlib.sha256((plain + salt).encode()).hexdigest()
            return hashed.split("$", 1)[1] == expected
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, is_admin: bool = False, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "is_admin": is_admin,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _try_decode(token: str, secret: str) -> Optional[dict]:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM], issuer=JWT_ISSUER, audience=JWT_AUDIENCE)
    except JWTError:
        return None


def decode_token(token: Optional[str]) -> dict:
    if not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _try_decode(token, SECRET_KEY)
    if payload is not None:
        return payload
    if SECRET_KEY_PREVIOUS:
        payload = _try_decode(token, SECRET_KEY_PREVIOUS)
        if payload is not None:
            return payload
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token non valido o scaduto",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    is_admin: bool = payload.get("is_admin", False)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        user_id_int = user_id
    return {"id": user_id_int, "is_admin": is_admin}


async def get_admin_user(token: str = Depends(oauth2_scheme)) -> dict:
    user = await get_current_user(token)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accesso amministratore richiesto")
    return user


async def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
