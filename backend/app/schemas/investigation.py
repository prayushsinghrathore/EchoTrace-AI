"""Investigation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.investigation import InvestigationPriority, InvestigationStatus


class InvestigationCreate(BaseModel):
    workspace_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    priority: InvestigationPriority = InvestigationPriority.MEDIUM
    lead_investigator: uuid.UUID | None = None


class InvestigationUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    status: InvestigationStatus | None = None
    priority: InvestigationPriority | None = None
    lead_investigator: uuid.UUID | None = None


class InvestigationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None = None
    status: InvestigationStatus
    priority: InvestigationPriority
    created_by: uuid.UUID
    lead_investigator: uuid.UUID | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    entity_count: int = 0
    relationship_count: int = 0
    evidence_count: int = 0
    timeline_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityCreate(BaseModel):
    type: str = Field(..., max_length=50)
    label: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    metadata_json: dict[str, Any] | None = None


class EntityUpdate(BaseModel):
    type: str | None = None
    label: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    metadata_json: dict[str, Any] | None = None


class EntityResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    type: str
    label: str
    description: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RelationshipCreate(BaseModel):
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str = Field(..., max_length=50)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    notes: str | None = Field(None, max_length=5000)


class RelationshipUpdate(BaseModel):
    relationship_type: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    notes: str | None = Field(None, max_length=5000)


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    confidence: float | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimelineEventCreate(BaseModel):
    event_timestamp: datetime
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    entity_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None


class TimelineEventUpdate(BaseModel):
    event_timestamp: datetime | None = None
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    entity_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None


class TimelineEventResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    event_timestamp: datetime
    title: str
    description: str | None = None
    entity_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceLinkCreate(BaseModel):
    evidence_id: uuid.UUID
    entity_id: uuid.UUID | None = None
    relationship: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=5000)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    color: str = "#6366f1"
    icon: str = ""


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: float | None = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class InvestigationSearchParams(BaseModel):
    query: str | None = Field(None, max_length=500)
    workspace_id: uuid.UUID | None = None
    status: InvestigationStatus | None = None
    priority: InvestigationPriority | None = None
    created_by: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class InvestigationSearchResponse(BaseModel):
    items: list[InvestigationResponse] = Field(default_factory=list)
    total: int = 0
    skip: int = 0
    limit: int = 50


class InvestigationDashboard(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    closed: int = 0
    entities: int = 0
    relationships: int = 0
    timeline_events: int = 0
