"""
User profile endpoints — retrieve and update the authenticated user's profile.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user, require_role
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import (
    PasswordChangeRequest,
    ProfileUpdateRequest,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
async def get_my_profile(
    user: User = Depends(get_current_user),
) -> User:
    """
    Retrieve the authenticated user's profile.

    Args:
        user: The authenticated user (injected by auth dependency).

    Returns:
        The user's public profile.
    """
    return user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Updates profile fields for the authenticated user.",
)
async def update_my_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Update the authenticated user's profile fields.

    Only provided fields are updated. Null fields are ignored.

    Args:
        body: Fields to update (display_name, avatar_url).
        user: The authenticated user.
        db: Database session.

    Returns:
        The updated user profile.
    """
    update_data = body.model_dump(exclude_none=True)

    if not update_data:
        return user

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    logger.info("Profile updated", user_id=str(user.id), fields=list(update_data.keys()))

    return user


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Change current user password",
    description="Verifies the current password and sets a new one.",
)
async def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Change the authenticated user's password.

    Verifies the current password before accepting the new one.

    Args:
        body: Current and new password.
        user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 400: Current password is incorrect.
    """
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.hashed_password = hash_password(body.new_password)
    await db.flush()

    logger.info("Password changed", user_id=str(user.id))


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
    description="Returns a list of all registered users. Admin role required.",
)
async def list_users(
    _user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> list[User]:
    """
    List all registered users.

    Restricted to admin role.

    Args:
        user: The authenticated admin user.
        db: Database session.

    Returns:
        List of all user profiles.
    """
    from sqlalchemy import select

    result = await db.execute(select(User))
    return list(result.scalars().all())
