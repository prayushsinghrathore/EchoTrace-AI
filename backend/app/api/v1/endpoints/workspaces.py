"""Workspace API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceDetailResponse, WorkspaceUpdate
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_ws(
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = WorkspaceService(db)
    return await svc.create(
        organization_id=body.organization_id,
        name=body.name,
        slug=body.slug,
        user_id=user.id,
        description=body.description,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_ws(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = WorkspaceService(db)
    return await svc.list_for_user(user.id)


@router.get("/{ws_id}", response_model=WorkspaceDetailResponse)
async def get_ws(
    ws_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = WorkspaceService(db)
    return await svc.get_with_counts(ws_id)


@router.patch("/{ws_id}", response_model=WorkspaceResponse)
async def update_ws(
    ws_id: uuid.UUID,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = WorkspaceService(db)
    return await svc.update(ws_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/{ws_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_ws(
    ws_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = WorkspaceService(db)
    await svc.delete(ws_id, user.id)
