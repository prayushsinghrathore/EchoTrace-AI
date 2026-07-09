"""Neo4j graph synchronization service.

Syncs SQL data to Neo4j for graph queries and visualization.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.logging import get_logger
from app.graph.neo4j import neo4j_manager
from app.models.entity import Entity
from app.models.relationship import Relationship

logger = get_logger(__name__)

# Type-to-color mapping for graph visualization
ENTITY_COLORS: dict[str, str] = {
    "person": "#ef4444",
    "email": "#f59e0b",
    "phone": "#10b981",
    "device": "#3b82f6",
    "file": "#8b5cf6",
    "domain": "#ec4899",
    "url": "#14b8a6",
    "ip": "#6366f1",
    "hash": "#84cc16",
    "account": "#f97316",
    "vehicle": "#06b6d4",
    "location": "#22c55e",
    "bank_account": "#e11d48",
    "crypto_wallet": "#a855f7",
    "custom": "#6b7280",
}

ENTITY_ICONS: dict[str, str] = {
    "person": "👤",
    "email": "📧",
    "phone": "📱",
    "device": "💻",
    "file": "📄",
    "domain": "🌐",
    "url": "🔗",
    "ip": "🌍",
    "hash": "#️⃣",
    "account": "👥",
    "vehicle": "🚗",
    "location": "📍",
    "bank_account": "🏦",
    "crypto_wallet": "₿",
    "custom": "📌",
}


class GraphSyncService:
    """Synchronizes investigation data between SQL and Neo4j."""

    async def sync_investigation(self, investigation_id: uuid.UUID) -> None:
        """Sync all entities and relationships for an investigation to Neo4j."""
        try:
            # Delete existing graph data for this investigation
            await neo4j_manager.execute_write(
                "MATCH (n:InvestigationNode {investigation_id: $inv_id}) DETACH DELETE n",
                {"inv_id": str(investigation_id)},
            )
            await neo4j_manager.execute_write(
                "MATCH (r:InvestigationRel {investigation_id: $inv_id}) DELETE r",
                {"inv_id": str(investigation_id)},
            )

            await self._sync_investigation_node(investigation_id)
            await self._sync_entities(investigation_id)
            await self._sync_relationships(investigation_id)
            logger.info("Graph synced for investigation", inv_id=str(investigation_id))
        except Exception as exc:
            logger.error("Graph sync failed", inv_id=str(investigation_id), error=str(exc))

    async def _sync_investigation_node(self, investigation_id: uuid.UUID) -> None:
        from app.db.session import AsyncSessionLocal
        from app.models.investigation import Investigation

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Investigation).where(Investigation.id == investigation_id))
            inv = result.scalar_one_or_none()
            if not inv:
                return

            await neo4j_manager.execute_write(
                """CREATE (n:InvestigationNode {
                    investigation_id: $inv_id, workspace_id: $ws_id,
                    title: $title, status: $status, priority: $priority
                })""",
                {
                    "inv_id": str(investigation_id),
                    "ws_id": str(inv.workspace_id),
                    "title": inv.title,
                    "status": inv.status.value if hasattr(inv.status, "value") else inv.status,
                    "priority": inv.priority.value if hasattr(inv.priority, "value") else inv.priority,
                },
            )

    async def _sync_entities(self, investigation_id: uuid.UUID) -> None:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Entity).where(Entity.investigation_id == investigation_id)
            )
            entities = result.scalars().all()

            for entity in entities:
                etype = entity.type.value if hasattr(entity.type, "value") else entity.type
                await neo4j_manager.execute_write(
                    """CREATE (n:EntityNode {
                        entity_id: $eid, investigation_id: $inv_id,
                        label: $label, type: $type,
                        color: $color, icon: $icon
                    })""",
                    {
                        "eid": str(entity.id),
                        "inv_id": str(investigation_id),
                        "label": entity.label,
                        "type": etype,
                        "color": ENTITY_COLORS.get(etype, "#6b7280"),
                        "icon": ENTITY_ICONS.get(etype, "📌"),
                    },
                )

    async def _sync_relationships(self, investigation_id: uuid.UUID) -> None:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Relationship).where(Relationship.investigation_id == investigation_id)
            )
            rels = result.scalars().all()

            for rel in rels:
                rtype = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type
                await neo4j_manager.execute_write(
                    """MATCH (a:EntityNode {entity_id: $src})
                       MATCH (b:EntityNode {entity_id: $tgt})
                       CREATE (a)-[r:RELATIONSHIP {
                           relationship_id: $rid, investigation_id: $inv_id,
                           type: $rtype, confidence: $confidence
                       }]->(b)""",
                    {
                        "rid": str(rel.id),
                        "inv_id": str(investigation_id),
                        "src": str(rel.source_entity_id),
                        "tgt": str(rel.target_entity_id),
                        "rtype": rtype,
                        "confidence": rel.confidence or 0.5,
                    },
                )

    async def rebuild_all(self) -> None:
        """Rebuild the entire Neo4j graph from SQL data."""
        await neo4j_manager.execute_write("MATCH (n) DETACH DELETE n")
        from app.db.session import AsyncSessionLocal
        from app.models.investigation import Investigation

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Investigation))
            investigations = result.scalars().all()
            for inv in investigations:
                await self.sync_investigation(inv.id)

        logger.info("Graph rebuild complete")
