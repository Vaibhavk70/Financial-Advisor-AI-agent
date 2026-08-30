"""User profile routes: fetch and update profile data."""
import json

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserUpdate
from app.utils.deps import get_current_active_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["👤 Users"])


# ─── 1. GET CURRENT USER PROFILE ─────────────────────────────────────
@router.get("/me",response_model=UserProfileResponse,summary="Get current user profile",)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    """Fetch profile data for the currently authenticated user."""
    # Parse stored JSON preferences string into a dictionary
    prefs = None
    if current_user.financial_preferences:
        try:
            prefs = json.loads(current_user.financial_preferences)
        except (json.JSONDecodeError, TypeError):
            prefs = None

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        financial_preferences=prefs,
    )


# ─── 2. UPDATE CURRENT USER PROFILE ──────────────────────────────────
@router.put("/me", response_model=UserProfileResponse, summary="Update current user profile")
async def update_my_profile(
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    """Update profile attributes (name or financial preferences)."""
    # Update full_name if provided
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    # Update financial_preferences if provided (serialize dict -> JSON string)
    if update_data.financial_preferences is not None:
        current_user.financial_preferences = json.dumps(
            update_data.financial_preferences,
            ensure_ascii=False,
        )

    await db.commit()
    await db.refresh(current_user)

    logger.info("User profile updated", user_id=current_user.id)

    # Parse JSON string back into dict for the response
    prefs = None
    if current_user.financial_preferences:
        prefs = json.loads(current_user.financial_preferences)

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        financial_preferences=prefs,
    )