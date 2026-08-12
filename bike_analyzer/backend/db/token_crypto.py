"""Token encryption at rest using Fernet symmetric encryption.

All OAuth tokens (access_token, refresh_token) and sync auth_tokens
must be encrypted before persisting to SQLite/PostgreSQL and decrypted
only when needed for API calls.
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_cipher: Fernet | None = None


def _get_key() -> bytes:
    key = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if not key:
        from bike_analyzer.backend.settings import get_settings
        _s = get_settings()
        key = getattr(_s, "token_encryption_key", "") or ""
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not configured. "
            "Set it in the environment (generate with: python -c \"import os; print(Fernet.generate_key().decode())\")"
        )
    key = key.strip().encode()
    if len(key) != 44 or not key.endswith(b"="):
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key (44 chars, base64-encoded)")
    return key


def get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        _cipher = Fernet(_get_key())
    return _cipher


def encrypt_token(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    cipher = get_cipher()
    return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    if not ciphertext:
        return ciphertext
    cipher = get_cipher()
    try:
        return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Token decryption failed: invalid token or wrong key")
        return ""
    except Exception:
        logger.warning("Token decryption failed", exc_info=True)
        return ""
