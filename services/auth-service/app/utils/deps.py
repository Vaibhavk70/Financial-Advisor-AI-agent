"""FastAPI dependencies: Redis client, current user extraction."""
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token

# ─── OAuth2 Scheme ───────────────────────────────────────────────────
# Points to the login endpoint where clients obtain tokens
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scheme_name="JWT Bearer",
)


# ─── Redis Dependency ────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """
    FastAPI dependency that provides a Redis connection per request.
    Used for: token blacklisting, refresh token storage, rate limiting.
    """
    redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    try:
        yield redis
    finally:
        await redis.aclose()


# ─── Current User Dependency ─────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    FastAPI dependency that validates a JWT access token and returns the User.
    
    Checks:
    1. Token is a valid JWT and not expired
    2. Token type is 'access' (not refresh)
    3. Token is not blacklisted in Redis (logged out)
    4. User exists in the database and is active
    """
    from app.models.user import User  # Avoid circular import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decode token
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    # 2. Extract user ID
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # 3. Check blacklist (user logged out)
    is_blacklisted = await redis.get(f"blacklist:access:{token[:16]}")  # Prefix check
    if is_blacklisted:
        raise credentials_exception

    # 4. Fetch user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Alias dependency — ensures user is active (used in routes for clarity)."""
    return current_user
