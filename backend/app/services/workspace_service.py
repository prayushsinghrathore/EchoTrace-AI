"""
Workspace service — manages workspaces within organizations.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func as sa_func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class WorkspaceService:
    """Business logic for workspace operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Workspace)

    async def _get_org(self, org_id: uuid.UUID) -> Organization:
        org_repo = BaseRepository(self.db, Organization)
        org = await org_repo.get(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return org

    async def _check_org_access(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Verify user can access the organization."""
        org = await self._get_org(org_id)
        if org.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def _get_member_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WorkspaceRole]:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        return member.role if member else None

    async def create(self, organization_id: uuid.UUID, name: str, slug: str, user_id: uuid.UUID, description: Optional[str] = None) -> Workspace:
        await self._check_org_access(organization_id, user_id)

        existing = await self.repo.find_one(slug=slug, organization_id=organization_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Workspace slug '{slug}' already exists in this organization")

        ws = Workspace(organization_id=organization_id, name=name, slug=slug, description=description)
        self.db.add(ws)
        await self.db.flush()
        await self.db.refresh(ws)

        # Add creator as OWNER member
        member = WorkspaceMember(workspace_id=ws.id, user_id=user_id, role=WorkspaceRole.OWNER)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(ws)

        logger.info("Workspace created", ws_id=str(ws.id), slug=slug, org=str(organization_id))
        return ws

    async def get(self, ws_id: uuid.UUID) -> Workspace:
        ws = await self.repo.get(ws_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        return ws

    async def get_with_counts(self, ws_id: uuid.UUID) -> dict:
        ws = await self.get(ws_id)
        from app.models.project import Project
        project_count = await BaseRepository(self.db, Project).count(workspace_id=ws_id)
        member_count = await BaseRepository(self.db, WorkspaceMember).count(workspace_id=ws_id)
        return {
            "id": ws.id,
            "organization_id": ws.organization_id,
            "name": ws.name,
            "slug": ws.slug,
            "description": ws.description,
            "created_at": ws.created_at,
            "updated_at": ws.updated_at,
            "project_count": project_count,
            "member_count": member_count,
        }

    async def list_for_org(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> list[Workspace]:
        await self._check_org_access(organization_id, user_id)
        return await self.repo.find_many(organization_id=organization_id, order_by="created_at", descending=True)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """List all workspaces where the user is a member."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, ws_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Workspace:
        ws = await self.get(ws_id)
        role = await self._get_member_role(ws_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        if "slug" in kwargs and kwargs["slug"]:
            existing = await self.repo.find_one(slug=kwargs["slug"], organization_id=ws.organization_id)
            if existing and existing.id != ws_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

        for key, val in kwargs.items():
            if val is not None and hasattr(ws, key):
                setattr(ws, key, val)
        await self.db.commit()
        await self.db.refresh(ws)
        return ws

    async def delete(self, ws_id: uuid.UUID, user_id: uuid.UUID) -> None:
        ws = await self.get(ws_id)
        role = await self._get_member_role(ws_id, user_id)
        if role != WorkspaceRole.OWNER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete the workspace")
        await self.db.execute(sa_delete(Workspace).where(Workspace.id == ws_id))
        await self.db.commit()
        logger.info("Workspace deleted", ws_id=str(ws_id))
