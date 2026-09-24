"""
Encryption/decryption utilities for GitHub access tokens.
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The key is stored in ENCRYPTION_KEY env var and never logged.
"""
import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet | None:
    key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        logger.error("ENCRYPTION_KEY is set but invalid — token encryption disabled")
        return None


def encrypt_token(token: str) -> str:
    """Encrypt a GitHub access token. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    if f is None:
        # Development fallback: base64-encode only (NOT secure, warns loudly)
        logger.warning("ENCRYPTION_KEY not set — storing token with base64 only (dev mode)")
        return base64.b64encode(token.encode()).decode()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str | None:
    """Decrypt an access token. Returns None on failure (key mismatch / corruption)."""
    f = _get_fernet()
    if f is None:
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            return None
    try:
        return f.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt access token — key mismatch or corrupted data")
        return None
