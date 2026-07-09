"""
User schemas — request and response models for user profile endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Public user profile returned from the API."""

    id: uuid.UUID = Field(..., description="Unique user identifier")
    email: str = Field(..., description="Email address")
    display_name: str | None = Field(None, description="Display name")
    avatar_url: str | None = Field(None, description="Avatar URL")
    role: str = Field(..., description="RBAC role")
    status: str = Field(..., description="Account status")
    is_verified: bool = Field(..., description="Email verified flag")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Schema for updating user profile fields."""

    display_name: str | None = Field(
        None,
        description="Display name",
        min_length=1,
        max_length=150,
    )
    avatar_url: str | None = Field(
        None,
        description="URL to avatar image",
        max_length=512,
    )


class PasswordChangeRequest(BaseModel):
    """Schema for password change requests."""

    current_password: str = Field(
        ...,
        description="Current password for verification",
        min_length=8,
    )
    new_password: str = Field(
        ...,
        description="New password (must meet complexity requirements)",
        min_length=8,
        max_length=128,
    )
