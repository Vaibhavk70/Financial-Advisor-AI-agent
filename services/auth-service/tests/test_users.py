"""Tests for user profile endpoints: GET /users/me and PUT /users/me."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/users/me"


async def get_auth_headers(client: AsyncClient, email_suffix: str = "profile") -> dict:
    """Helper fixture function: registers user, logs in, and returns Authorization header."""
    email = f"{email_suffix}@example.com"
    await client.post(REGISTER_URL, json={
        "email": email,
        "full_name": "Profile Test User",
        "password": "SecurePass123",
    })
    resp = await client.post(LOGIN_URL, data={
        "username": email,
        "password": "SecurePass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── 1. GET PROFILE TESTS ─────────────────────────────────────────────
class TestGetProfile:

    async def test_get_profile_success(self, client: AsyncClient):
        """Verify fetching user profile with valid Bearer token."""
        headers = await get_auth_headers(client, "get_ok")
        response = await client.get(ME_URL, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "get_ok@example.com"
        assert data["full_name"] == "Profile Test User"
        assert "id" in data
        assert "hashed_password" not in data

    async def test_get_profile_unauthorized(self, client: AsyncClient):
        """Verify fetching profile without token fails with HTTP 401."""
        response = await client.get(ME_URL)
        assert response.status_code == 401

    async def test_get_profile_invalid_token(self, client: AsyncClient):
        """Verify fetching profile with fake token fails with HTTP 401."""
        response = await client.get(ME_URL, headers={"Authorization": "Bearer fake.jwt.token"})
        assert response.status_code == 401


# ─── 2. UPDATE PROFILE TESTS ──────────────────────────────────────────
class TestUpdateProfile:

    async def test_update_name_success(self, client: AsyncClient):
        """Verify updating user display name."""
        headers = await get_auth_headers(client, "update_name")
        response = await client.put(ME_URL, json={"full_name": "Updated Name"}, headers=headers)
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"

    async def test_update_financial_preferences(self, client: AsyncClient):
        """Verify updating financial preferences dictionary."""
        headers = await get_auth_headers(client, "update_prefs")
        prefs = {
            "risk_tolerance": "moderate",
            "investment_goals": ["wealth_creation", "tax_saving"],
            "monthly_income_range": "50000-100000",
            "preferred_assets": ["mutual_funds"],
            "investment_horizon_years": 5,
        }
        response = await client.put(
            ME_URL,
            json={"financial_preferences": prefs},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["financial_preferences"]["risk_tolerance"] == "moderate"
        assert "mutual_funds" in data["financial_preferences"]["preferred_assets"]

    async def test_update_empty_body(self, client: AsyncClient):
        """Verify empty update payload returns profile unchanged."""
        headers = await get_auth_headers(client, "empty_update")
        response = await client.put(ME_URL, json={}, headers=headers)
        assert response.status_code == 200

    async def test_update_name_too_short(self, client: AsyncClient):
        """Verify name shorter than 2 chars fails validation with HTTP 422."""
        headers = await get_auth_headers(client, "short_name")
        response = await client.put(ME_URL, json={"full_name": "A"}, headers=headers)
        assert response.status_code == 422

    async def test_update_unauthorized(self, client: AsyncClient):
        """Verify update attempt without token fails with HTTP 401."""
        response = await client.put(ME_URL, json={"full_name": "Hacker"})
        assert response.status_code == 401