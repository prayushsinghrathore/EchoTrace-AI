"""
Authentication endpoints — register, login, token refresh, logout, password reset.

Supports both Bearer token (header) and HTTPOnly cookie auth strategies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limiter import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
    decode_password_reset_token,
    generate_token_id,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.user import UserResponse

logger = get_logger(__name__)

router = APIRouter(tags=["authentication"])


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request, respecting proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HTTPOnly secure cookies for token transport."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


async def _revoke_user_refresh_tokens(
    db: AsyncSession,
    user_id: str,
    action: str = "logout",
    exclude_jti: str | None = None,
) -> None:
    """
    Revoke all active refresh tokens for a user.

    Args:
        db: Database session.
        user_id: The user whose tokens to revoke.
        action: Reason for revocation.
        exclude_jti: Optional JWT ID to exclude (keep this token active).
    """
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == uuid.UUID(user_id),
        RefreshToken.is_revoked == False,  # noqa: E712
    )
    if exclude_jti:
        stmt = stmt.where(RefreshToken.token_jti != exclude_jti)

    result = await db.execute(stmt)
    tokens = result.scalars().all()

    for token in tokens:
        token.revoke(action=action)

    if tokens:
        logger.info(
            "Revoked refresh tokens",
            user_id=user_id,
            count=len(tokens),
            action=action,
        )


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: RegisterRequest,
    _rate_limit: None = Depends(rate_limit("register")),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Create a new user account."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("User registered", user_id=str(user.id), email=user.email, role=user.role.value)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(rate_limit("login")),
) -> dict[str, Any]:
    """
    Authenticate user, audit login attempt, issue JWT tokens.

    Supports both Bearer header and HTTPOnly cookie strategies.
    Tracks IP, failed attempts, and last_login metadata.
    """
    client_ip = _get_client_ip(request)

    # Look up user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        # Record failed attempt if user exists
        if user is not None:
            user.record_failed_login()
            await db.flush()
            logger.warning(
                "Failed login attempt",
                user_id=str(user.id),
                email=body.email,
                ip=client_ip,
                attempts=user.failed_login_attempts,
            )
        else:
            logger.warning("Failed login attempt (unknown user)", email=body.email, ip=client_ip)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is {user.status.value}",
        )

    # Record successful login
    user.record_successful_login(ip_address=client_ip)
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # Generate tokens with rotation support
    token_id = generate_token_id()
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        token_id=token_id,
    )

    # Persist refresh token for rotation/revocation tracking
    token_hash = hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_jti=token_id,
        token_hash=token_hash,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
        expires_at=expires_at,
    )
    db.add(db_refresh_token)
    await db.commit()

    logger.info(
        "User logged in",
        user_id=str(user.id),
        email=user.email,
        ip=client_ip,
    )

    result_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # Set HTTPOnly cookies if configured
    if settings.AUTH_USE_COOKIES:
        _set_auth_cookies(response, access_token, refresh_token)

    return result_data


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(rate_limit("refresh")),
) -> dict[str, Any]:
    """
    Exchange a refresh token for a new token pair.

    Implements token rotation:
    - Validates the provided refresh token
    - Verifies it exists in the database and is not revoked
    - Revokes the old token (rotation)
    - Issues a new access + refresh token pair
    """
    client_ip = _get_client_ip(request)
    raw_token = body.refresh_token

    # Decode JWT
    try:
        payload = decode_token(raw_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Use a refresh token.",
        )

    token_jti = payload.get("jti")
    user_id = payload.get("sub")

    if not token_jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    # Look up stored token record
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_jti == token_jti,
            RefreshToken.user_id == uuid.UUID(user_id),
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        # Token not in DB — could be a replay of a rotated token
        # Revoke all tokens for this user as a security measure
        await _revoke_user_refresh_tokens(db, user_id, action="rotation_replay")
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found. All sessions have been revoked as a security precaution.",
        )

    if stored_token.is_revoked:
        # Token was already revoked — possible token theft
        # Revoke all tokens for this user
        await _revoke_user_refresh_tokens(db, user_id, action="theft_detected")
        await db.commit()
        logger.warning(
            "Revoked all sessions — revoked refresh token was reused",
            user_id=user_id,
            token_jti=token_jti,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This token has been revoked. All sessions have been invalidated.",
        )

    if stored_token.is_expired:
        stored_token.revoke(action="expired")
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )

    # Verify the token matches stored hash
    if not verify_token(raw_token, stored_token.token_hash):
        stored_token.revoke(action="hash_mismatch")
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature verification failed",
        )

    # Verify user exists and is active
    user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        stored_token.revoke(action="user_inactive")
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # ── ROTATION: Revoke the old token ──────────────────────────────────
    stored_token.revoke(action="rotation")

    # Generate new token pair with new JTI
    new_token_id = generate_token_id()
    access_token = create_access_token(
        subject=str(user_id),
        extra_claims={"role": user.role.value, "email": user.email},
    )
    new_refresh_token = create_refresh_token(
        subject=str(user_id),
        token_id=new_token_id,
    )

    # Persist the new refresh token
    new_token_hash = hash_token(new_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    new_db_token = RefreshToken(
        user_id=uuid.UUID(user_id),
        token_jti=new_token_id,
        token_hash=new_token_hash,
        rotated_from_jti=token_jti,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
        expires_at=expires_at,
    )
    db.add(new_db_token)
    await db.commit()

    logger.debug("Tokens refreshed (rotated)", user_id=user_id)

    result_data = TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    if settings.AUTH_USE_COOKIES:
        _set_auth_cookies(response, access_token, new_refresh_token)

    return result_data


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Logout — revoke all refresh tokens",
    description="Revokes all active refresh tokens for the authenticated user.",
)
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Logout — revoke all active refresh tokens for this user.

    Client should discard access and refresh tokens after this call.
    """
    await _revoke_user_refresh_tokens(db, str(user.id), action="logout")
    await db.commit()

    if settings.AUTH_USE_COOKIES:
        _clear_auth_cookies(response)

    logger.info("User logged out", user_id=str(user.id))


# ── Password Reset ──────────────────────────────────────────────────────────


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset",
    description="Sends a password reset token to the user's email (mocked in development).",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(rate_limit("reset")),
) -> dict[str, str]:
    """
    Initiate a password reset.

    If the email exists, a reset token is generated and stored.
    In production, this would be emailed to the user.
    In development, the token is logged.

    Always returns 200 to prevent email enumeration attacks.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user is None:
        logger.info(
            "Password reset requested for unknown email",
            email=body.email,
        )
        return {
            "message": "If the email exists, a reset link has been sent.",
        }

    # Generate reset token
    reset_token = create_password_reset_token(str(user.id))
    token_hash = hash_token(reset_token)

    from datetime import timedelta

    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
    )

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_record)
    await db.commit()

    # In development, log the token instead of sending email
    if settings.is_development:
        logger.info(
            "Password reset token (dev mode)",
            user_id=str(user.id),
            email=user.email,
            reset_token=reset_token,
            reset_link=f"{settings.PASSWORD_RESET_URL or 'http://localhost:3000'}"
                       f"/auth/reset-password?token={reset_token}",
        )
    else:
        # In production, this would send an email
        logger.info(
            "Password reset initiated",
            user_id=str(user.id),
            email=user.email,
        )

    return {
        "message": "If the email exists, a reset link has been sent.",
    }


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset password using a reset token",
    description="Validates the reset token and sets a new password.",
)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(rate_limit("reset")),
) -> dict[str, str]:
    """
    Complete a password reset using a valid token.

    Validates the token, verifies it hasn't been used, and sets the new password.
    """
    client_ip = _get_client_ip(request)

    # Decode and validate the reset token JWT
    try:
        payload = decode_password_reset_token(body.token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Request a new one.",
        )
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or malformed reset token.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token payload.",
        )

    # Look up the reset record by user
    token_hash = hash_token(body.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == uuid.UUID(user_id),
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used == False,  # noqa: E712
        )
    )
    reset_record = result.scalar_one_or_none()

    if reset_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token.",
        )

    if reset_record.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Request a new one.",
        )

    # Load the user and update the password
    user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    # Update password
    user.hashed_password = hash_password(body.new_password)

    # Mark reset record as used
    reset_record.mark_used(ip_address=client_ip)

    # Revoke all existing sessions as a security measure
    await _revoke_user_refresh_tokens(db, user_id, action="password_reset")
    await db.commit()

    logger.info(
        "Password reset completed",
        user_id=user_id,
        email=user.email,
        ip=client_ip,
    )

    return {
        "message": "Password has been reset successfully. You can now log in.",
    }
