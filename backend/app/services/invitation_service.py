"""
Invitation service — manages workspace invitations.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.invitation import Invitation
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class InvitationService:
    """Business logic for workspace invitation operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Invitation)

    async def _check_admin(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        if member.role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Owner role required")

    async def invite(self, workspace_id: uuid.UUID, email: str, role: WorkspaceRole, invited_by: uuid.UUID) -> Invitation:
        await self._check_admin(workspace_id, invited_by)

        # Check for pending invitation to same email + workspace
        existing = await self.repo.find_one(workspace_id=workspace_id, email=email, accepted_at=None, declined_at=None)
        if existing and not existing.is_expired:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending invitation already exists for this email")

        # Check if user is already a member
        user_result = await self.db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
        if user:
            member_repo = BaseRepository(self.db, WorkspaceMember)
            existing_member = await member_repo.find_one(workspace_id=workspace_id, user_id=user.id)
            if existing_member:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this workspace")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = Invitation(
            workspace_id=workspace_id,
            email=email,
            invited_by=invited_by,
            role=role,
            token=token,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)

        logger.info("Invitation created", ws_id=str(workspace_id), email=email, role=role.value)
        return invitation

    async def accept(self, token: str, user_id: uuid.UUID) -> dict:
        invitation = await self.repo.find_one(token=token)
        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invitation.is_expired:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")
        if invitation.is_accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already accepted")
        if invitation.is_declined:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already declined")

        invitation.accept()

        member = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role=invitation.role,
        )
        self.db.add(member)
        await self.db.commit()

        logger.info("Invitation accepted", ws_id=str(invitation.workspace_id), user=str(user_id))
        return {"message": "Invitation accepted", "workspace_id": str(invitation.workspace_id)}

    async def decline(self, token: str) -> dict:
        invitation = await self.repo.find_one(token=token)
        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invitation.is_accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already accepted")
        if invitation.is_declined:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already declined")

        invitation.decline()
        await self.db.commit()

        logger.info("Invitation declined", ws_id=str(invitation.workspace_id), email=invitation.email)
        return {"message": "Invitation declined"}

    async def list_for_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[Invitation]:
        await self._check_admin(workspace_id, user_id)
        return await self.repo.find_many(workspace_id=workspace_id, order_by="created_at", descending=True)

    async def list_pending_for_user(self, email: str) -> list[Invitation]:
        return await self.repo.find_many(email=email, accepted_at=None, declined_at=None)
