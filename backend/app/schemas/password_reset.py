"""
Password reset schemas — request models for the reset flow.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset email."""

    email: str = Field(
        ...,
        description="Registered email address",
        examples=["user@example.com"],
        max_length=320,
    )


class ResetPasswordRequest(BaseModel):
    """Schema for performing a password reset."""

    token: str = Field(
        ...,
        description="Password reset token received via email",
    )
    new_password: str = Field(
        ...,
        description="New password (must meet complexity requirements)",
        min_length=8,
        max_length=128,
    )


class ForgotPasswordResponse(BaseModel):
    """Response after requesting a password reset."""

    message: str = Field(
        ...,
        description="Human-readable status message",
        examples=["If the email exists, a reset link has been sent."],
    )


class ResetPasswordResponse(BaseModel):
    """Response after successfully resetting a password."""

    message: str = Field(
        ...,
        description="Success message",
        examples=["Password has been reset successfully. You can now log in."],
    )
