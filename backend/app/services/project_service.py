"""
Project service — manages investigation projects.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.project import Project, ProjectStatus
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ProjectService:
    """Business logic for project operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Project)

    async def _get_member_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WorkspaceRole]:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        return member.role if member else None

    async def _check_member_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole:
        role = await self._get_member_role(workspace_id, user_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        return role

    async def _check_ws_exists(self, ws_id: uuid.UUID) -> Workspace:
        ws_repo = BaseRepository(self.db, Workspace)
        ws = await ws_repo.get(ws_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        return ws

    async def create(self, workspace_id: uuid.UUID, name: str, slug: str, user_id: uuid.UUID, description: Optional[str] = None) -> Project:
        await self._check_ws_exists(workspace_id)
        role = await self._check_member_access(workspace_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to create projects")

        existing = await self.repo.find_one(slug=slug, workspace_id=workspace_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project slug '{slug}' already exists in this workspace")

        project = Project(workspace_id=workspace_id, name=name, slug=slug, description=description)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        logger.info("Project created", project_id=str(project.id), slug=slug, ws=str(workspace_id))
        return project

    async def get(self, project_id: uuid.UUID) -> Project:
        proj = await self.repo.get(project_id)
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return proj

    async def list_for_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[Project]:
        await self._check_ws_exists(workspace_id)
        await self._check_member_access(workspace_id, user_id)
        return await self.repo.find_many(workspace_id=workspace_id, order_by="created_at", descending=True)

    async def update(self, project_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Project:
        proj = await self.get(project_id)
        await self._check_member_access(proj.workspace_id, user_id)

        if "slug" in kwargs and kwargs["slug"]:
            existing = await self.repo.find_one(slug=kwargs["slug"], workspace_id=proj.workspace_id)
            if existing and existing.id != project_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

        for key, val in kwargs.items():
            if val is not None and hasattr(proj, key):
                setattr(proj, key, val)
        await self.db.commit()
        await self.db.refresh(proj)
        return proj

    async def delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        proj = await self.get(project_id)
        role = await self._check_member_access(proj.workspace_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to delete projects")
        await self.db.execute(sa_delete(Project).where(Project.id == project_id))
        await self.db.commit()
        logger.info("Project deleted", project_id=str(project_id))
