"""Tests for authentication endpoints: register, login, refresh, and health."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"

VALID_USER = {
    "email": "vaibhav@example.com",
    "full_name": "Vaibhav Sharma",
    "password": "SecurePass123",
}


# ─── 1. REGISTER TESTS ────────────────────────────────────────────────
class TestRegister:

    async def test_register_success(self, client: AsyncClient):
        """Verify successful user registration."""
        response = await client.post(REGISTER_URL, json=VALID_USER)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == VALID_USER["email"]
        assert data["full_name"] == VALID_USER["full_name"]
        assert "id" in data
        assert "hashed_password" not in data  # Never leak password in API response!
        assert data["is_active"] is True

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Verify duplicate registration fails with HTTP 400."""
        await client.post(REGISTER_URL, json=VALID_USER)
        response = await client.post(REGISTER_URL, json=VALID_USER)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        """Verify invalid email fails Pydantic validation with HTTP 422."""
        response = await client.post(REGISTER_URL, json={
            **VALID_USER,
            "email": "invalid-email-format",
        })
        assert response.status_code == 422

    async def test_register_weak_passwords(self, client: AsyncClient):
        """Verify weak passwords fail validation."""
        # Short password (< 8 chars)
        resp1 = await client.post(REGISTER_URL, json={**VALID_USER, "email": "a@ex.com", "password": "Short1"})
        assert resp1.status_code == 422

        # No uppercase letter
        resp2 = await client.post(REGISTER_URL, json={**VALID_USER, "email": "b@ex.com", "password": "nouppercase123"})
        assert resp2.status_code == 422

        # No digit
        resp3 = await client.post(REGISTER_URL, json={**VALID_USER, "email": "c@ex.com", "password": "NoDigitPassword"})
        assert resp3.status_code == 422


# ─── 2. LOGIN TESTS ───────────────────────────────────────────────────
class TestLogin:

    async def test_login_success(self, client: AsyncClient):
        """Verify successful login returns valid JWT tokens."""
        await client.post(REGISTER_URL, json={**VALID_USER, "email": "login_ok@example.com"})
        response = await client.post(LOGIN_URL, data={
            "username": "login_ok@example.com",
            "password": "SecurePass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Verify wrong password fails with HTTP 401."""
        await client.post(REGISTER_URL, json={**VALID_USER, "email": "wrongpass@example.com"})
        response = await client.post(LOGIN_URL, data={
            "username": "wrongpass@example.com",
            "password": "WrongPassword999",
        })
        assert response.status_code == 401

    async def test_login_jwt_structure(self, client: AsyncClient):
        """Verify access token is a valid 3-part JWT (header.payload.signature)."""
        await client.post(REGISTER_URL, json={**VALID_USER, "email": "jwt_structure@example.com"})
        resp = await client.post(LOGIN_URL, data={
            "username": "jwt_structure@example.com",
            "password": "SecurePass123",
        })
        token = resp.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3, "JWT must contain exactly 3 parts separated by dots"


# ─── 3. REFRESH TOKEN TESTS ───────────────────────────────────────────
class TestRefreshToken:

    async def test_refresh_success(self, client: AsyncClient, mock_redis):
        """Verify refreshing an access token using a valid refresh token."""
        await client.post(REGISTER_URL, json={**VALID_USER, "email": "refresh_user@example.com"})
        login_resp = await client.post(LOGIN_URL, data={
            "username": "refresh_user@example.com",
            "password": "SecurePass123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        # Mock Redis returning stored refresh token
        mock_redis.get.return_value = refresh_token

        response = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Verify invalid refresh token fails with HTTP 401."""
        response = await client.post(REFRESH_URL, json={"refresh_token": "fake.jwt.token"})
        assert response.status_code == 401


# ─── 4. HEALTH CHECK TESTS ────────────────────────────────────────────
class TestHealthCheck:

    async def test_health_endpoint(self, client: AsyncClient):
        """Verify /health returns HTTP 200 healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"