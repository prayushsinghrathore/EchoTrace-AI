"""Workspace member schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.workspace_member import WorkspaceRole


class MemberAddRequest(BaseModel):
    user_id: uuid.UUID
    role: WorkspaceRole = WorkspaceRole.VIEWER


class MemberUpdateRequest(BaseModel):
    role: WorkspaceRole


class MemberResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class MemberWithUserResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str = ""
    display_name: Optional[str] = None
    role: WorkspaceRole
    joined_at: datetime

    model_config = {"from_attributes": True}
