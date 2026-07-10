"""
Audit service — records immutable enterprise audit trail entries.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import AuditAction, AuditLog
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class AuditService:
    """Records and queries immutable audit log entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BaseRepository(db, AuditLog)

    async def record(
        self,
        action: AuditAction,
        user_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        success: bool = True,
        error_detail: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata_json,
            success=success,
            error_detail=error_detail,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list(
        self,
        workspace_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        action: AuditAction | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        filters: dict[str, Any] = {}
        if workspace_id:
            filters["workspace_id"] = workspace_id
        if user_id:
            filters["user_id"] = user_id
        if action:
            filters["action"] = action
        entries = await self.repo.find_many(
            **filters, order_by="timestamp", descending=True, skip=skip, limit=limit
        )
        total = await self.repo.count(**filters)
        return entries, total
