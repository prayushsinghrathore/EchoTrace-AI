"""
Notification service — manages user notifications.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification import Notification, NotificationType
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class NotificationService:
    """Business logic for user notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BaseRepository(db, Notification)

    async def create(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str | None = None,
        workspace_id: uuid.UUID | None = None,
        link: str | None = None,
        actor_id: uuid.UUID | None = None,
        reference_id: str | None = None,
        reference_type: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            workspace_id=workspace_id,
            link=link,
            actor_id=actor_id,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        self.db.add(notification)
        await self.db.flush()
        logger.debug("Notification created", user_id=str(user_id), type=notification_type.value)
        return notification

    async def notify_workspace_members(
        self,
        workspace_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str | None = None,
        exclude_user_id: uuid.UUID | None = None,
        link: str | None = None,
        actor_id: uuid.UUID | None = None,
        reference_id: str | None = None,
        reference_type: str | None = None,
    ) -> list[Notification]:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        members = await member_repo.find_many(workspace_id=workspace_id)
        created = []
        for member in members:
            if exclude_user_id and member.user_id == exclude_user_id:
                continue
            n = await self.create(
                user_id=member.user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                workspace_id=workspace_id,
                link=link,
                actor_id=actor_id,
                reference_id=reference_id,
                reference_type=reference_type,
            )
            created.append(n)
        return created

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Notification], int]:
        filters: dict[str, Any] = {"user_id": user_id}
        if unread_only:
            filters["is_read"] = False
        notifications = await self.repo.find_many(
            **filters, order_by="created_at", descending=True, skip=skip, limit=limit
        )
        total = await self.repo.count(**filters)
        return notifications, total

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        n = await self.repo.get(notification_id)
        if not n or n.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        n.mark_read()
        await self.db.commit()
        await self.db.refresh(n)
        return n

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.count(user_id=user_id, is_read=False)
