"""
Authentication and authorization dependencies.

Provides FastAPI dependency injection for:
- Extracting and validating JWT tokens from requests (Bearer header + cookies)
- Loading the current authenticated user
- Checking RBAC roles and permissions

Supports dual authentication strategies:
1. Bearer token via Authorization header (primary for API clients)
2. HTTPOnly cookie (primary for browser-based access when enabled)
"""

from __future__ import annotations

import uuid
from typing import Any

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.models.user import User, UserRole, UserStatus

logger = get_logger(__name__)

# HTTP Bearer token extractor (auto_error=False — we handle the None case)
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    auto_error=False,
)


class AuthError(HTTPException):
    """Base authentication error."""

    def __init__(self, detail: str, error_code: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_code = error_code


class ForbiddenError(HTTPException):
    """Authorization error (insufficient permissions)."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def _extract_token_from_cookie(request: Request) -> str | None:
    """
    Extract JWT access token from HTTPOnly cookie.

    Fallback strategy when Bearer header is not provided.
    Only used when AUTH_USE_COOKIES is enabled.
    """
    if not settings.AUTH_USE_COOKIES:
        return None
    return request.cookies.get("access_token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
    request: Request = None,  # type: ignore[assignment]
) -> User:
    """
    Dependency: extract and validate JWT, return the authenticated user.

    Token extraction priority:
    1. Authorization: Bearer header
    2. HTTPOnly access_token cookie (if AUTH_USE_COOKIES is enabled)

    Must be used as a dependency on any protected endpoint.

    Args:
        credentials: Bearer token from the Authorization header.
        db: Database session.
        request: FastAPI request (for cookie extraction).

    Returns:
        The authenticated User instance.

    Raises:
        AuthError (401): If no token, invalid token, or user not found.
    """
    token: str | None = None

    # Try Bearer header first
    if credentials is not None:
        token = credentials.credentials

    # Fall back to cookie if configured
    if token is None and settings.AUTH_USE_COOKIES and request is not None:
        token = _extract_token_from_cookie(request)

    if token is None:
        raise AuthError(
            detail="Authentication required",
            error_code="MISSING_TOKEN",
        )

    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise AuthError(
            detail="Token has expired",
            error_code="TOKEN_EXPIRED",
        ) from None
    except pyjwt.PyJWTError as exc:
        logger.warning("Invalid token", error=str(exc))
        raise AuthError(
            detail="Invalid or malformed token",
            error_code="INVALID_TOKEN",
        ) from exc

    # Verify it's an access token
    token_type = payload.get("type")
    if token_type != "access":
        raise AuthError(
            detail="Invalid token type. Use an access token.",
            error_code="INVALID_TOKEN_TYPE",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError(
            detail="Token missing subject claim",
            error_code="INVALID_TOKEN",
        )

    # Load user from database
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("Token user not found", user_id=user_id)
        raise AuthError(
            detail="User not found",
            error_code="USER_NOT_FOUND",
        )

    # Check account status
    if user.status != UserStatus.ACTIVE:
        raise AuthError(
            detail=f"Account is {user.status.value}",
            error_code="ACCOUNT_INACTIVE",
        )

    logger.debug("Authenticated user", user_id=str(user.id), role=user.role.value)
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
    request: Request = None,  # type: ignore[assignment]
) -> User | None:
    """
    Dependency: like get_current_user, but returns None if no token provided.

    Useful for endpoints that behave differently for authenticated users
    but are also accessible anonymously.
    """
    if credentials is None and not (
        settings.AUTH_USE_COOKIES and request is not None and request.cookies.get("access_token")
    ):
        return None

    try:
        return await get_current_user(credentials, db, request)
    except AuthError:
        return None


# ── RBAC Dependencies ──────────────────────────────────────────────────────


def require_role(*roles: UserRole) -> Any:
    """
    Dependency factory: require at least one of the specified roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...

        @router.get("/staff")
        async def staff_endpoint(
            user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
        ):
            ...
    """

    async def _role_checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user

        if user.role not in roles:
            raise ForbiddenError(
                detail=f"Requires one of: {', '.join(r.value for r in roles)}",
            )
        return user

    return _role_checker


def require_permission(action: str, resource: str = "*") -> Any:
    """
    Dependency factory: check a specific permission.

    Args:
        action: The action (e.g., "create", "read", "update", "delete").
        resource: The resource (e.g., "users", "traces", "workspaces").

    This is a placeholder for a more granular permission system.
    Currently maps to role-based checks as follows:
        - admin: all actions on all resources
        - user: read/update on own resources
        - viewer: read only
        - auditor: read only
    """

    async def _permission_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if user.is_superuser:
            return user

        if user.role == UserRole.ADMIN:
            return user  # Full access

        if user.role == UserRole.USER:
            if action in ("read", "update") or resource == "*":
                return user
            raise ForbiddenError(detail=f"User role cannot '{action}' on '{resource}'")

        if user.role in (UserRole.VIEWER, UserRole.AUDITOR):
            if action == "read":
                return user
            raise ForbiddenError(
                detail=f"{user.role.value} role is read-only, cannot '{action}'",
            )

        raise ForbiddenError()

    return _permission_checker
