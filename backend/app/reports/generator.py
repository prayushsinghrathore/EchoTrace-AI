"""
ReportGenerator — gathers investigation data and produces structured ReportData.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.chain_of_custody import ChainOfCustodyEvent
from app.models.entity import Entity
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.timeline_event import TimelineEvent
from app.reports.schemas import ReportData, ReportMetadata
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ReportGenerator:
    """Gathers investigation data and builds a structured ReportData object."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_ai: bool = True,  # noqa: ARG002
        include_custody: bool = True,
    ) -> ReportData:
        inv_repo = BaseRepository(self.db, Investigation)
        investigation = await inv_repo.get(investigation_id)
        if not investigation:
            raise ValueError("Investigation not found")

        # Build metadata
        meta = ReportMetadata(
            title=f"Investigation Report: {investigation.title}",
            investigation_id=investigation_id,
            workspace_id=investigation.workspace_id,
            generated_by=user_id,
            generated_at=datetime.now(UTC),
            format="markdown",
        )

        # Evidence
        ev_repo = BaseRepository(self.db, Evidence)
        evidence_items = await ev_repo.find_many(
            workspace_id=investigation.workspace_id, is_deleted=False, limit=500
        )
        evidence_summary_lines = []
        timeline_events_raw = []
        entities_raw = []
        relationships_raw = []
        custody_list = []
        stats = {}

        for ev in evidence_items:
            evidence_summary_lines.append({
                "id": str(ev.id),
                "number": ev.evidence_number,
                "title": ev.title,
                "category": ev.category,
                "status": ev.status.value if hasattr(ev.status, "value") else ev.status,
                "priority": ev.priority.value if hasattr(ev.priority, "value") else ev.priority,
                "filename": ev.original_filename,
                "hash": ev.sha256_hash,
                "file_size": ev.file_size,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })

        # Timeline
        tl_repo = BaseRepository(self.db, TimelineEvent)
        tl_events = await tl_repo.find_many(
            investigation_id=investigation_id, order_by="event_timestamp"
        )
        for te in tl_events:
            timeline_events_raw.append({
                "date": te.event_timestamp.isoformat() if te.event_timestamp else "",
                "title": te.title,
                "description": te.description or "",
            })

        # Entities
        ent_repo = BaseRepository(self.db, Entity)
        entities = await ent_repo.find_many(investigation_id=investigation_id)
        for e in entities:
            etype = e.type.value if hasattr(e.type, "value") else e.type
            entities_raw.append({
                "type": etype,
                "label": e.label,
                "description": e.description or "",
            })

        # Relationships
        rel_repo = BaseRepository(self.db, Relationship)
        rels = await rel_repo.find_many(investigation_id=investigation_id)
        for r in rels:
            rtype = r.relationship_type.value if hasattr(r.relationship_type, "value") else r.relationship_type
            relationships_raw.append({
                "source": str(r.source_entity_id),
                "target": str(r.target_entity_id),
                "type": rtype,
                "confidence": r.confidence,
                "notes": r.notes or "",
            })

        # Chain of custody
        if include_custody:
            ev_ids = [ev.id for ev in evidence_items]
            if ev_ids:
                cust_repo = BaseRepository(self.db, ChainOfCustodyEvent)
                for eid in ev_ids[:20]:
                    events = await cust_repo.find_many(evidence_id=eid, order_by="timestamp", limit=10)
                    for ce in events:
                        custody_list.append({
                            "evidence_id": str(ce.evidence_id),
                            "action": ce.action,
                            "user_id": str(ce.user_id),
                            "timestamp": ce.timestamp.isoformat() if ce.timestamp else "",
                            "notes": ce.notes or "",
                        })

        # Statistics
        stats = {
            "total_evidence": len(evidence_items),
            "total_entities": len(entities),
            "total_relationships": len(rels),
            "total_timeline_events": len(tl_events),
            "total_custody_events": len(custody_list),
        }

        return ReportData(
            metadata=meta,
            executive_summary=f"Investigation report for {investigation.title}.",
            evidence_summary="\n".join(
                f"- **{e['title']}** ({e['number']}) - {e['category']} [{e['status']}]"
                for e in evidence_summary_lines
            ) or "No evidence recorded.",
            timeline=timeline_events_raw,
            entities=entities_raw,
            relationships=relationships_raw,
            findings=[],
            recommendations=[],
            chain_of_custody=custody_list,
            statistics=stats,
        )
