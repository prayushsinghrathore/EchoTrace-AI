"""
Authentication schemas — request and response models for auth endpoints.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """Schema for user registration requests."""

    email: str = Field(
        ...,
        description="User email address (also used as login identifier)",
        examples=["user@example.com"],
        max_length=320,
    )
    password: str = Field(
        ...,
        description="Password (min 8, must contain uppercase, lowercase, digit)",
        min_length=8,
        max_length=128,
        examples=["SecureP@ss1"],
    )
    display_name: str = Field(
        ...,
        description="Display name shown in the UI",
        min_length=1,
        max_length=150,
        examples=["Jane Doe"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize and validate email format."""
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password complexity requirements."""
        errors: list[str] = []

        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("an uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("a lowercase letter")
        if not re.search(r"\d", v):
            errors.append("a digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", v):
            errors.append("a special character")

        if errors:
            raise ValueError(
                f"Password must contain: {', '.join(errors)}"
            )

        return v


class LoginRequest(BaseModel):
    """Schema for login requests."""

    email: str = Field(
        ...,
        description="Registered email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="Account password",
        examples=["SecureP@ss1"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """Schema returned on successful authentication."""

    access_token: str = Field(..., description="JWT access token (short-lived)")
    refresh_token: str = Field(..., description="JWT refresh token (long-lived)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token TTL in seconds")


class RefreshRequest(BaseModel):
    """Schema for token refresh requests."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload."""

    sub: str = Field(..., description="Token subject (user ID)")
    exp: int = Field(..., description="Token expiry timestamp")
    iat: int = Field(..., description="Token issued-at timestamp")
    type: str = Field(..., description="Token type: access or refresh")


class AuthError(BaseModel):
    """Schema for authentication error responses."""

    detail: str = Field(..., description="Error description")
    error_code: str | None = Field(None, description="Machine-readable error code")
