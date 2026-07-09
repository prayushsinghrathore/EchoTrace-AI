"""Investigation service — core business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import func as sa_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.graph.graph_sync import ENTITY_COLORS, ENTITY_ICONS, GraphSyncService
from app.models.entity import Entity
from app.models.investigation import Investigation, InvestigationStatus
from app.models.relationship import Relationship
from app.models.timeline_event import TimelineEvent
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class InvestigationService:
    """Business logic for investigation operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inv_repo = BaseRepository(db, Investigation)
        self.entity_repo = BaseRepository(db, Entity)
        self.rel_repo = BaseRepository(db, Relationship)
        self.timeline_repo = BaseRepository(db, TimelineEvent)
        self.graph_sync = GraphSyncService()

    async def _check_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        return member.role

    async def _check_investigator(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self._check_member(workspace_id, user_id)
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # ── Investigations ──────────────────────────────────────────────────

    async def create(self, workspace_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Investigation:
        await self._check_investigator(workspace_id, user_id)
        inv = Investigation(
            workspace_id=workspace_id,
            created_by=user_id,
            **kwargs,
        )
        self.db.add(inv)
        await self.db.commit()
        await self.db.refresh(inv)
        logger.info("Investigation created", inv_id=str(inv.id))
        return inv

    async def get(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> Investigation:
        inv = await self.inv_repo.get(inv_id)
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
        await self._check_member(inv.workspace_id, user_id)
        return inv

    async def update(self, inv_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Investigation:
        inv = await self.get(inv_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)

        if kwargs.get("status") == InvestigationStatus.CLOSED:
            kwargs["closed_at"] = datetime.now(UTC)
        elif kwargs.get("status") in (InvestigationStatus.OPEN, InvestigationStatus.IN_PROGRESS):
            kwargs["closed_at"] = None

        for key, val in kwargs.items():
            if val is not None and hasattr(inv, key):
                setattr(inv, key, val)
        await self.db.commit()
        await self.db.refresh(inv)
        return inv

    async def delete(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> None:
        inv = await self.get(inv_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        await self.db.execute(sa_delete(Investigation).where(Investigation.id == inv_id))
        await self.db.commit()

    async def list_for_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
        await self._check_member(workspace_id, user_id)
        invs = await self.inv_repo.find_many(
            workspace_id=workspace_id, order_by="created_at", descending=True
        )
        return await self._enrich_list(invs)

    async def search(self, params: dict, user_id: uuid.UUID) -> tuple[list[dict], int]:
        query = select(Investigation)

        subq = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        query = query.where(Investigation.workspace_id.in_(subq))

        if params.get("query"):
            q = f"%{params['query']}%"
            query = query.where(
                or_(
                    Investigation.title.ilike(q),
                    Investigation.description.ilike(q),
                )
            )
        for field in ("workspace_id", "status", "priority", "created_by"):
            if params.get(field):
                query = query.where(getattr(Investigation, field) == params[field])
        if params.get("date_from"):
            query = query.where(Investigation.created_at >= params["date_from"])
        if params.get("date_to"):
            query = query.where(Investigation.created_at <= params["date_to"])

        count_result = await self.db.execute(select(sa_func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        query = query.order_by(Investigation.created_at.desc())
        query = query.offset(params.get("skip", 0)).limit(params.get("limit", 50))
        result = await self.db.execute(query)
        invs = list(result.scalars().all())
        items = await self._enrich_list(invs)
        return items, total

    async def _enrich_list(self, invs: list[Investigation]) -> list[dict]:
        result = []
        for inv in invs:
            ec = await self.entity_repo.count(investigation_id=inv.id)
            rc = await self.rel_repo.count(investigation_id=inv.id)
            tc = await self.timeline_repo.count(investigation_id=inv.id)
            result.append({
                "id": inv.id,
                "workspace_id": inv.workspace_id,
                "title": inv.title,
                "description": inv.description,
                "status": inv.status.value if hasattr(inv.status, "value") else inv.status,
                "priority": inv.priority.value if hasattr(inv.priority, "value") else inv.priority,
                "created_by": str(inv.created_by),
                "lead_investigator": str(inv.lead_investigator) if inv.lead_investigator else None,
                "opened_at": inv.opened_at.isoformat() if inv.opened_at else None,
                "closed_at": inv.closed_at.isoformat() if inv.closed_at else None,
                "entity_count": ec,
                "relationship_count": rc,
                "timeline_count": tc,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
            })
        return result

    async def get_dashboard(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        await self._check_member(workspace_id, user_id)
        invs = await self.inv_repo.find_many(workspace_id=workspace_id)
        total = len(invs)
        open_count = sum(1 for i in invs if i.status == InvestigationStatus.OPEN)
        in_progress = sum(1 for i in invs if i.status == InvestigationStatus.IN_PROGRESS)
        closed = sum(1 for i in invs if i.status == InvestigationStatus.CLOSED)

        entity_total = 0
        rel_total = 0
        timeline_total = 0
        for inv in invs:
            entity_total += await self.entity_repo.count(investigation_id=inv.id)
            rel_total += await self.rel_repo.count(investigation_id=inv.id)
            timeline_total += await self.timeline_repo.count(investigation_id=inv.id)

        return {
            "total": total,
            "open": open_count,
            "in_progress": in_progress,
            "closed": closed,
            "entities": entity_total,
            "relationships": rel_total,
            "timeline_events": timeline_total,
        }

    # ── Entities ────────────────────────────────────────────────────────

    async def create_entity(self, inv_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Entity:
        inv = await self.get(inv_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)

        entity = Entity(
            investigation_id=inv_id,
            created_by=user_id,
            type=kwargs["type"],
            label=kwargs["label"],
            description=kwargs.get("description"),
            metadata_json=kwargs.get("metadata_json"),
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        await self.graph_sync.sync_investigation(inv_id)
        return entity

    async def update_entity(self, entity_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Entity:
        entity_repo = BaseRepository(self.db, Entity)
        entity = await entity_repo.get(entity_id)
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
        inv = await self.get(entity.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)

        for key, val in kwargs.items():
            if val is not None and hasattr(entity, key):
                setattr(entity, key, val)
        await self.db.commit()
        await self.db.refresh(entity)
        await self.graph_sync.sync_investigation(entity.investigation_id)
        return entity

    async def delete_entity(self, entity_id: uuid.UUID, user_id: uuid.UUID) -> None:
        entity_repo = BaseRepository(self.db, Entity)
        entity = await entity_repo.get(entity_id)
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
        inv = await self.get(entity.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        await entity_repo.delete(entity_id, hard=True)
        await self.db.commit()
        await self.graph_sync.sync_investigation(entity.investigation_id)

    async def list_entities(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> list[Entity]:
        await self.get(inv_id, user_id)
        return await self.entity_repo.find_many(investigation_id=inv_id, order_by="created_at")

    # ── Relationships ───────────────────────────────────────────────────

    async def create_relationship(self, inv_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Relationship:
        inv = await self.get(inv_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)

        rel = Relationship(
            investigation_id=inv_id,
            **kwargs,
        )
        self.db.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)
        await self.graph_sync.sync_investigation(inv_id)
        return rel

    async def update_relationship(self, rel_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Relationship:
        rel_repo = BaseRepository(self.db, Relationship)
        rel = await rel_repo.get(rel_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
        inv = await self.get(rel.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)

        for key, val in kwargs.items():
            if val is not None and hasattr(rel, key):
                setattr(rel, key, val)
        await self.db.commit()
        await self.db.refresh(rel)
        await self.graph_sync.sync_investigation(rel.investigation_id)
        return rel

    async def delete_relationship(self, rel_id: uuid.UUID, user_id: uuid.UUID) -> None:
        rel_repo = BaseRepository(self.db, Relationship)
        rel = await rel_repo.get(rel_id)
        if not rel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
        inv = await self.get(rel.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        await rel_repo.delete(rel_id, hard=True)
        await self.db.commit()
        await self.graph_sync.sync_investigation(rel.investigation_id)

    async def list_relationships(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
        await self.get(inv_id, user_id)
        rels = await self.rel_repo.find_many(investigation_id=inv_id, order_by="created_at")
        result = []
        for rel in rels:
            result.append({
                "id": rel.id,
                "investigation_id": rel.investigation_id,
                "source_entity_id": rel.source_entity_id,
                "target_entity_id": rel.target_entity_id,
                "relationship_type": rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type,
                "confidence": rel.confidence,
                "notes": rel.notes,
                "created_at": rel.created_at,
                "updated_at": rel.updated_at,
            })
        return result

    # ── Timeline ────────────────────────────────────────────────────────

    async def create_timeline_event(self, inv_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> TimelineEvent:
        inv = await self.get(inv_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        event = TimelineEvent(investigation_id=inv_id, created_by=user_id, **kwargs)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def update_timeline_event(self, event_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> TimelineEvent:
        event = await self.timeline_repo.get(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline event not found")
        inv = await self.get(event.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        for key, val in kwargs.items():
            if val is not None and hasattr(event, key):
                setattr(event, key, val)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete_timeline_event(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        event = await self.timeline_repo.get(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline event not found")
        inv = await self.get(event.investigation_id, user_id)
        await self._check_investigator(inv.workspace_id, user_id)
        await self.timeline_repo.delete(event_id, hard=True)
        await self.db.commit()

    async def list_timeline_events(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> list[TimelineEvent]:
        await self.get(inv_id, user_id)
        return await self.timeline_repo.find_many(
            investigation_id=inv_id, order_by="event_timestamp", descending=False
        )

    # ── Graph ──────────────────────────────────────────────────────────

    async def get_graph(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        await self.get(inv_id, user_id)
        entities = await self.entity_repo.find_many(investigation_id=inv_id)
        rels = await self.rel_repo.find_many(investigation_id=inv_id)

        nodes = []
        seen = set()
        for e in entities:
            eid = str(e.id)
            if eid not in seen:
                seen.add(eid)
                etype = e.type.value if hasattr(e.type, "value") else e.type
                nodes.append({
                    "id": eid,
                    "label": e.label,
                    "type": etype,
                    "color": ENTITY_COLORS.get(etype, "#6b7280"),
                    "icon": ENTITY_ICONS.get(etype, "📌"),
                })

        edges = []
        for r in rels:
            rtype = r.relationship_type.value if hasattr(r.relationship_type, "value") else r.relationship_type
            edges.append({
                "id": str(r.id),
                "source": str(r.source_entity_id),
                "target": str(r.target_entity_id),
                "type": rtype,
                "confidence": r.confidence,
            })

        return {"nodes": nodes, "edges": edges}

    async def sync_graph(self, inv_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        await self.get(inv_id, user_id)
        await self.graph_sync.sync_investigation(inv_id)
        return await self.get_graph(inv_id, user_id)
