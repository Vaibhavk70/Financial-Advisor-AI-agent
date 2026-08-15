"""Pydantic schemas for JWT token requests and responses."""
from pydantic import BaseModel


class Token(BaseModel):
    """Response schema returned on login or token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Internal schema representing decoded JWT payload contents."""
    sub: str | None = None   # User ID
    type: str | None = None  # 'access' or 'refresh'


class RefreshTokenRequest(BaseModel):
    """Request body schema for POST /auth/refresh endpoint."""
    refresh_token: str


class LogoutResponse(BaseModel):
    """Response body schema for POST /auth/logout endpoint."""
    message: str = "Successfully logged out"