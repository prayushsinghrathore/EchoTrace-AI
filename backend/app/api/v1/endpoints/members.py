"""Workspace member API endpoints — mounted under /workspaces."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.member import MemberAddRequest, MemberResponse, MemberUpdateRequest, MemberWithUserResponse
from app.services.member_service import MemberService

router = APIRouter(tags=["members"])


@router.get("/{ws_id}/members", response_model=list[MemberWithUserResponse])
async def list_members(
    ws_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = MemberService(db)
    return await svc.list_members(ws_id, user.id)


@router.post("/{ws_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    ws_id: uuid.UUID,
    body: MemberAddRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = MemberService(db)
    return await svc.add_member(ws_id, body.user_id, body.role, user.id)


@router.patch("/{ws_id}/members/{member_id}", response_model=MemberResponse)
async def update_member(
    ws_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = MemberService(db)
    return await svc.update_member(ws_id, member_id, body.role, user.id)


@router.delete("/{ws_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def remove_member(
    ws_id: uuid.UUID,
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = MemberService(db)
    await svc.remove_member(ws_id, member_id, user.id)
