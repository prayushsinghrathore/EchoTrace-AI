"""Investigation API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.investigation import (
    EntityCreate,
    EntityResponse,
    EntityUpdate,
    InvestigationCreate,
    InvestigationResponse,
    InvestigationUpdate,
    RelationshipCreate,
    RelationshipResponse,
    RelationshipUpdate,
    TimelineEventCreate,
    TimelineEventResponse,
    TimelineEventUpdate,
)
from app.services.investigation_service import InvestigationService

router = APIRouter(tags=["investigations"])


# ── Investigations ─────────────────────────────────────────────────────────

@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    body: InvestigationCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.create(workspace_id=body.workspace_id, user_id=user.id, **body.model_dump(exclude={"workspace_id"}))


@router.get("/workspace/{workspace_id}", response_model=list)
async def list_investigations(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.list_for_workspace(workspace_id, user.id)


@router.get("/search", response_model=dict)
async def search_investigations(
    q: str | None = Query(None),
    workspace_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    params = {"query": q, "workspace_id": workspace_id, "status": status, "priority": priority,
              "skip": skip, "limit": limit}
    items, total = await svc.search(params, user.id)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/dashboard/{workspace_id}", response_model=dict)
async def investigation_dashboard(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.get_dashboard(workspace_id, user.id)


@router.get("/{inv_id}", response_model=InvestigationResponse)
async def get_investigation(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.get(inv_id, user.id)


@router.patch("/{inv_id}", response_model=InvestigationResponse)
async def update_investigation(
    inv_id: uuid.UUID,
    body: InvestigationUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.update(inv_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/{inv_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_investigation(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    await svc.delete(inv_id, user.id)


# ── Entities ───────────────────────────────────────────────────────────────

@router.post("/{inv_id}/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    inv_id: uuid.UUID,
    body: EntityCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.create_entity(inv_id, user.id, **body.model_dump())


@router.get("/{inv_id}/entities", response_model=list[EntityResponse])
async def list_entities(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.list_entities(inv_id, user.id)


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: uuid.UUID,
    body: EntityUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.update_entity(entity_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_entity(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    await svc.delete_entity(entity_id, user.id)


# ── Relationships ──────────────────────────────────────────────────────────

@router.post("/{inv_id}/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    inv_id: uuid.UUID,
    body: RelationshipCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.create_relationship(inv_id, user.id, **body.model_dump())


@router.get("/{inv_id}/relationships", response_model=list[RelationshipResponse])
async def list_relationships(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.list_relationships(inv_id, user.id)


@router.patch("/relationships/{rel_id}", response_model=RelationshipResponse)
async def update_relationship(
    rel_id: uuid.UUID,
    body: RelationshipUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.update_relationship(rel_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_relationship(
    rel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    await svc.delete_relationship(rel_id, user.id)


# ── Timeline ───────────────────────────────────────────────────────────────

@router.post("/{inv_id}/timeline", response_model=TimelineEventResponse, status_code=status.HTTP_201_CREATED)
async def create_timeline_event(
    inv_id: uuid.UUID,
    body: TimelineEventCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.create_timeline_event(inv_id, user.id, **body.model_dump())


@router.get("/{inv_id}/timeline", response_model=list[TimelineEventResponse])
async def list_timeline_events(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.list_timeline_events(inv_id, user.id)


@router.patch("/timeline/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(
    event_id: uuid.UUID,
    body: TimelineEventUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.update_timeline_event(event_id, user.id, **body.model_dump(exclude_none=True))


@router.delete("/timeline/{event_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_timeline_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    await svc.delete_timeline_event(event_id, user.id)


# ── Graph ──────────────────────────────────────────────────────────────────

@router.get("/{inv_id}/graph", response_model=dict)
async def get_graph(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.get_graph(inv_id, user.id)


@router.post("/{inv_id}/graph/sync", response_model=dict)
async def sync_graph(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = InvestigationService(db)
    return await svc.sync_graph(inv_id, user.id)
