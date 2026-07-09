"""Invitation API endpoints — split for proper routing."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.invitation import InvitationAccept, InvitationCreate, InvitationDecline, InvitationResponse
from app.services.invitation_service import InvitationService

# Router for workspace-nested invitation routes (mounted under /workspaces)
ws_router = APIRouter(tags=["invitations"])

# Router for standalone invitation routes (mounted at root level)
router = APIRouter(tags=["invitations"])


@ws_router.post("/{ws_id}/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    ws_id: uuid.UUID,
    body: InvitationCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvitationService(db)
    return await svc.invite(ws_id, body.email, body.role, user.id)


@ws_router.get("/{ws_id}/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    ws_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvitationService(db)
    return await svc.list_for_workspace(ws_id, user.id)


@router.post("/invite/accept")
async def accept_invite(
    body: InvitationAccept,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvitationService(db)
    return await svc.accept(body.token, user.id)


@router.post("/invite/decline")
async def decline_invite(
    body: InvitationDecline,
    db: AsyncSession = Depends(get_db_session),
):
    svc = InvitationService(db)
    return await svc.decline(body.token)
