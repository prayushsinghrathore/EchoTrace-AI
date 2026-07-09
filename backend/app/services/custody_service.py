"""Chain of custody service — records immutable events."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.chain_of_custody import ChainOfCustodyEvent
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class CustodyService:
    """Records and queries chain of custody events."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, ChainOfCustodyEvent)

    async def record(self, evidence_id: uuid.UUID, user_id: uuid.UUID,
                     action: str, notes: Optional[str] = None,
                     ip_address: Optional[str] = None,
                     request_id: Optional[str] = None,
                     details: Optional[str] = None) -> ChainOfCustodyEvent:
        """Record an immutable custody event."""
        event = ChainOfCustodyEvent(
            evidence_id=evidence_id,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            request_id=request_id,
            notes=notes,
            details=details,
        )
        self.db.add(event)
        await self.db.flush()
        logger.debug("Custody event recorded", ev_id=str(evidence_id), action=action)
        return event

    async def list_for_evidence(self, evidence_id: uuid.UUID) -> list[ChainOfCustodyEvent]:
        return await self.repo.find_many(evidence_id=evidence_id, order_by="timestamp", descending=True)

    async def count_for_evidence(self, evidence_id: uuid.UUID) -> int:
        return await self.repo.count(evidence_id=evidence_id)
