"""
Activity service — records and retrieves workspace activity events.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.activity_event import ActivityEvent, ActivityEventType
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ActivityService:
    """Records and queries activity timeline events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BaseRepository(db, ActivityEvent)

    async def record(
        self,
        workspace_id: uuid.UUID,
        actor_id: uuid.UUID,
        event_type: ActivityEventType,
        title: str,
        description: str | None = None,
        investigation_id: uuid.UUID | None = None,
        metadata_json: dict | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            workspace_id=workspace_id,
            actor_id=actor_id,
            investigation_id=investigation_id,
            event_type=event_type,
            title=title,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(event)
        await self.db.flush()
        logger.debug("Activity recorded", ws_id=str(workspace_id), type=event_type.value)
        return event

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: uuid.UUID | None = None,
        event_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ActivityEvent], int]:
        await self._check_member(workspace_id, user_id)
        filters: dict[str, Any] = {"workspace_id": workspace_id}
        if investigation_id:
            filters["investigation_id"] = investigation_id
        if event_type:
            try:
                filters["event_type"] = ActivityEventType(event_type)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid event type: {event_type}") from None
        events = await self.repo.find_many(**filters, order_by="occurred_at", descending=True, skip=skip, limit=limit)
        total = await self.repo.count(**filters)
        return events, total

    async def list_for_investigation(
        self,
        investigation_id: uuid.UUID,
        _user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ActivityEvent], int]:
        filters: dict[str, Any] = {"investigation_id": investigation_id}
        events = await self.repo.find_many(**filters, order_by="occurred_at", descending=True, skip=skip, limit=limit)
        total = await self.repo.count(**filters)
        return events, total

    async def _check_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
