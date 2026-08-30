"""Authentication routes: register, login, refresh, and logout."""
from datetime import timedelta

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.token import LogoutResponse, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.utils.deps import get_current_user, get_redis

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["🔐 Authentication"])


# ─── 1. REGISTER ──────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Create a new user account with hashed password."""
    # Check if email is already registered
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create new user instance
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    logger.info("User registered", user_id=new_user.id, email=new_user.email)
    return new_user  # type: ignore[return-value]


# ─── 2. LOGIN ─────────────────────────────────────────────────────────
@router.post("/login", response_model=Token, summary="Login and obtain JWT tokens")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Token:
    """OAuth2 compatible login returning access + refresh tokens."""
    # Fetch user by email (OAuth2 form passes email inside username field)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated",
        )

    # Create tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    # Store refresh token in Redis with 7-day TTL
    await redis.setex(
        name=f"refresh_token:{user.id}",
        time=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        value=refresh_token,
    )

    logger.info("User logged in successfully", user_id=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


# ─── 3. REFRESH TOKEN ─────────────────────────────────────────────────
@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Token:
    """Exchange a valid refresh token for a fresh token pair."""
    invalid_token_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    # Decode and verify payload
    payload = decode_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise invalid_token_error

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise invalid_token_error

    # Verify refresh token matches stored Redis token (detect reuse attacks)
    stored_token = await redis.get(f"refresh_token:{user_id}")
    if stored_token != token_data.refresh_token:
        logger.warning("Refresh token mismatch / reuse attempt", user_id=user_id)
        raise invalid_token_error

    # Check user active status
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise invalid_token_error

    # Generate NEW token pair (Refresh Token Rotation)
    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)

    # Overwrite refresh token in Redis
    await redis.setex(
        name=f"refresh_token:{user.id}",
        time=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        value=new_refresh_token,
    )

    logger.info("Tokens refreshed successfully", user_id=user.id)
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


# ─── 4. LOGOUT ────────────────────────────────────────────────────────
@router.post("/logout", response_model=LogoutResponse, summary="Logout and revoke tokens")
async def logout(
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> LogoutResponse:
    """Logout current user by revoking their refresh token in Redis."""
    await redis.delete(f"refresh_token:{current_user.id}")
    logger.info("User logged out", user_id=current_user.id)
    return LogoutResponse()