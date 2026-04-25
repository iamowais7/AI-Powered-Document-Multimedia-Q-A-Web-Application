import pytest
from httpx import AsyncClient
from app.models.user import User


pytestmark = pytest.mark.asyncio


async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "securepass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    response = await client.post("/api/v1/auth/register", json={
        "email": test_user.email,
        "username": "uniqueuser123",
        "password": "password123",
    })
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


async def test_register_duplicate_username(client: AsyncClient, test_user: User):
    response = await client.post("/api/v1/auth/register", json={
        "email": "unique@example.com",
        "username": test_user.username,
        "password": "password123",
    })
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


async def test_register_invalid_username(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "valid@example.com",
        "username": "x",  # too short
        "password": "password123",
    })
    assert response.status_code == 422


async def test_register_weak_password(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "valid@example.com",
        "username": "validuser",
        "password": "short",  # < 8 chars
    })
    assert response.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "username": "validuser",
        "password": "password123",
    })
    assert response.status_code == 422


async def test_login_success(client: AsyncClient, test_user: User):
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email


async def test_login_wrong_password(client: AsyncClient, test_user: User):
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "wrongpassword",
    })
    assert response.status_code == 401


async def test_login_wrong_email(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert response.status_code == 401


async def test_get_me(client: AsyncClient, test_user: User, auth_headers: dict):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


async def test_get_me_no_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
