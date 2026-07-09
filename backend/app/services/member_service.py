"""
Member service — manages workspace membership.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class MemberService:
    """Business logic for workspace member operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, WorkspaceMember)

    async def _get_member_role(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WorkspaceRole]:
        member = await self.repo.find_one(workspace_id=workspace_id, user_id=user_id)
        return member.role if member else None

    async def _check_admin(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceMember:
        member = await self.repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        if member.role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Owner role required")
        return member

    async def list_members(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
        """List all members of a workspace with user details.

        Uses a single JOIN query to avoid N+1 lookups for user enrichment.
        """
        role = await self._get_member_role(workspace_id, user_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")

        stmt = (
            select(WorkspaceMember, User)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": m.id,
                "user_id": m.user_id,
                "email": u.email if u else "",
                "display_name": u.display_name if u else None,
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m, u in rows
        ]

    async def add_member(self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, role: WorkspaceRole, actor_id: uuid.UUID) -> WorkspaceMember:
        await self._check_admin(workspace_id, actor_id)

        existing = await self.repo.find_one(workspace_id=workspace_id, user_id=target_user_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this workspace")

        member = WorkspaceMember(workspace_id=workspace_id, user_id=target_user_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        logger.info("Member added", ws_id=str(workspace_id), user=str(target_user_id), role=role.value)
        return member

    async def update_member(self, workspace_id: uuid.UUID, member_id: uuid.UUID, role: WorkspaceRole, actor_id: uuid.UUID) -> WorkspaceMember:
        await self._check_admin(workspace_id, actor_id)

        member = await self.repo.get(member_id)
        if not member or member.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # Cannot change role of OWNER
        if member.role == WorkspaceRole.OWNER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change the owner's role")

        member.role = role
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, workspace_id: uuid.UUID, member_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        await self._check_admin(workspace_id, actor_id)

        member = await self.repo.get(member_id)
        if not member or member.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        if member.role == WorkspaceRole.OWNER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the workspace owner")

        await self.db.execute(sa_delete(WorkspaceMember).where(WorkspaceMember.id == member_id))
        await self.db.commit()
        logger.info("Member removed", ws_id=str(workspace_id), user=str(member.user_id))
