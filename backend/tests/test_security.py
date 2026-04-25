import pytest
from datetime import timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_hash_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert len(hashed) > 20


def test_verify_password_correct():
    hashed = hash_password("correctpassword")
    assert verify_password("correctpassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correctpassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token():
    token = create_access_token({"sub": "1", "email": "test@test.com"})
    assert isinstance(token, str)
    assert len(token) > 20


def test_create_access_token_custom_expiry():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)


def test_decode_token_valid():
    token = create_access_token({"sub": "42", "email": "x@x.com"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "x@x.com"


def test_decode_token_invalid():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_decode_token_expired():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_success(db_session):
    from app.core.security import get_current_user
    from app.models.user import User
    from app.core.security import hash_password, create_access_token
    from unittest.mock import MagicMock

    user = User(id=1, email="u@u.com", username="usr", hashed_password=hash_password("p"), is_active=True)
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})

    credentials = MagicMock()
    credentials.credentials = token

    result = await get_current_user(credentials=credentials, db=db_session)
    assert result.email == "u@u.com"


@pytest.mark.asyncio
async def test_get_current_user_no_sub(db_session):
    from app.core.security import get_current_user
    from unittest.mock import MagicMock

    token = create_access_token({"email": "x@x.com"})  # no sub
    credentials = MagicMock()
    credentials.credentials = token

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found(db_session):
    from app.core.security import get_current_user
    from unittest.mock import MagicMock

    token = create_access_token({"sub": "99999", "email": "ghost@ghost.com"})
    credentials = MagicMock()
    credentials.credentials = token

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)
    assert exc_info.value.status_code == 401
