"""Invitation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.workspace_member import WorkspaceRole


class InvitationCreate(BaseModel):
    workspace_id: uuid.UUID
    email: str = Field(..., max_length=320)
    role: WorkspaceRole = WorkspaceRole.VIEWER


class InvitationAccept(BaseModel):
    token: str = Field(..., min_length=1)


class InvitationDecline(BaseModel):
    token: str = Field(..., min_length=1)


class InvitationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    email: str
    invited_by: uuid.UUID
    role: WorkspaceRole
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
