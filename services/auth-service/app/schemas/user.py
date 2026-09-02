"""Pydantic schemas for User request validation and response formatting."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── 1. Request Schemas (Data coming IN) ─────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration request (POST /auth/register)."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255, examples=["Vaibhav Sharma"])
    password: str = Field(..., min_length=8, max_length=128, examples=["SecurePass123"])

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password security rules: must contain uppercase + digit."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return v.strip()


class UserUpdate(BaseModel):
    """Schema for updating user profile (PUT /users/me). All fields optional."""
    full_name: str | None = Field(None, min_length=2, max_length=255)
    financial_preferences: dict[str, Any] | None = Field(
        None,
        examples=[{
            "risk_tolerance": "moderate",
            "investment_goals": ["wealth_creation", "tax_saving"],
            "monthly_income_range": "50000-100000",
            "preferred_assets": ["mutual_funds", "stocks"],
            "investment_horizon_years": 5,
        }],
    )


# ─── 2. Response Schemas (Data going OUT) ────────────────────────────

class UserResponse(BaseModel):
    """Schema for user data returned in API responses (hides password!)."""
    id: str
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    # Tells Pydantic to read data directly from SQLAlchemy ORM attributes
    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    """Extended user response including financial preferences dictionary."""
    financial_preferences: dict[str, Any] | None = None

    model_config = {"from_attributes": True}