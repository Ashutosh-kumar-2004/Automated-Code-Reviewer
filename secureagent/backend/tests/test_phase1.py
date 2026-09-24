"""
Unit tests for Phase 1:
- HS256 JWT creation and validation
- Auth middleware helpers
- IDOR ownership helpers
- User upsert logic
"""
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import get_settings
from app.middleware.auth import ALGORITHM, decode_bff_token

settings = get_settings()


# ── JWT Tests ─────────────────────────────────────────────────────────────────

def make_token(
    user_id: str = "test-user-id",
    expire_offset: int = 600,
    secret: str | None = None,
) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expire_offset,
    }
    return jwt.encode(payload, secret or settings.backend_secret, algorithm=ALGORITHM)


def test_valid_token_decodes():
    token = make_token()
    payload = decode_bff_token(token)
    assert payload["sub"] == "test-user-id"


def test_expired_token_raises_401():
    token = make_token(expire_offset=-1)  # already expired
    with pytest.raises(HTTPException) as exc:
        decode_bff_token(token)
    assert exc.value.status_code == 401


def test_wrong_secret_raises_401():
    token = make_token(secret="wrong-secret-here-32-chars------")
    with pytest.raises(HTTPException) as exc:
        decode_bff_token(token)
    assert exc.value.status_code == 401


def test_malformed_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_bff_token("not.a.valid.jwt")
    assert exc.value.status_code == 401


def test_token_missing_sub_field():
    """Token with no 'sub' should be rejected by get_current_user (not by decode)."""
    payload = {"iat": int(time.time()), "exp": int(time.time()) + 600}
    token = jwt.encode(payload, settings.backend_secret, algorithm=ALGORITHM)
    decoded = decode_bff_token(token)
    # decode itself doesn't fail, but sub is missing
    assert decoded.get("sub") is None


# ── IDOR helper tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_owned_repo_wrong_user_raises_403():
    from app.middleware.auth import get_owned_repo
    from app.models.repository import Repository
    from app.models.user import User

    repo = Repository(
        id="repo-1",
        user_id="other-user-id",
        github_repo_id="123",
        full_name="other/repo",
        clone_url="https://github.com/other/repo.git",
        html_url="https://github.com/other/repo",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = repo
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    user = User(id="current-user-id", github_id="gh1", login="me")

    with pytest.raises(HTTPException) as exc:
        await get_owned_repo("repo-1", user, mock_db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_owned_repo_not_found_raises_404():
    from app.middleware.auth import get_owned_repo
    from app.models.user import User

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    user = User(id="current-user-id", github_id="gh1", login="me")

    with pytest.raises(HTTPException) as exc:
        await get_owned_repo("nonexistent", user, mock_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_owned_repo_correct_user_returns_repo():
    from app.middleware.auth import get_owned_repo
    from app.models.repository import Repository
    from app.models.user import User

    repo = Repository(
        id="repo-1",
        user_id="current-user-id",
        github_repo_id="123",
        full_name="me/repo",
        clone_url="https://github.com/me/repo.git",
        html_url="https://github.com/me/repo",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = repo
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    user = User(id="current-user-id", github_id="gh1", login="me")

    result = await get_owned_repo("repo-1", user, mock_db)
    assert result.id == "repo-1"


# ── Crypto tests ──────────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet
    from app.services.crypto import decrypt_token, encrypt_token

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    token = "ghp_supersecrettoken123"
    encrypted = encrypt_token(token)
    assert encrypted != token
    decrypted = decrypt_token(encrypted)
    assert decrypted == token


def test_decrypt_with_wrong_key_returns_none(monkeypatch):
    from cryptography.fernet import Fernet
    from app.services.crypto import decrypt_token, encrypt_token

    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()

    monkeypatch.setenv("ENCRYPTION_KEY", key1)
    encrypted = encrypt_token("some-token")

    monkeypatch.setenv("ENCRYPTION_KEY", key2)
    result = decrypt_token(encrypted)
    assert result is None


# ── Security score formula ────────────────────────────────────────────────────

def test_security_score_formula():
    from app.models.scan import Scan

    assert Scan.compute_security_score(0, 0, 0, 0) == 100.0
    assert Scan.compute_security_score(1, 0, 0, 0) == 90.0    # -10
    assert Scan.compute_security_score(0, 2, 0, 0) == 90.0    # -5×2
    assert Scan.compute_security_score(0, 0, 5, 0) == 90.0    # -2×5
    assert Scan.compute_security_score(10, 10, 10, 10) == 0.0 # capped at 0
    # 100 - 2×10 - 4×5 - 5×2 - 2×0.5 = 100 - 20 - 20 - 10 - 1 = 49
    assert Scan.compute_security_score(2, 4, 5, 2) == 49.0


def test_security_score_never_negative():
    from app.models.scan import Scan
    assert Scan.compute_security_score(100, 100, 100, 100) == 0.0
