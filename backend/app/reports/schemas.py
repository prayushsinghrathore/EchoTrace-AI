"""
Report schemas — structured data models for investigation reports.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    order: int = 0


class ReportMetadata(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    investigation_id: uuid.UUID
    workspace_id: uuid.UUID
    generated_by: uuid.UUID
    generated_at: datetime | None = None
    format: str = "markdown"
    version: str = "1.0"


class ReportData(BaseModel):
    metadata: ReportMetadata
    executive_summary: str = ""
    evidence_summary: str = ""
    timeline: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    chain_of_custody: list[dict] = Field(default_factory=list)
    statistics: dict = Field(default_factory=dict)


class ReportGenerateRequest(BaseModel):
    investigation_id: uuid.UUID
    include_ai_findings: bool = True
    include_recommendations: bool = True
    include_custody: bool = True
    format: str = "markdown"


class ReportExportRequest(BaseModel):
    investigation_id: uuid.UUID
    format: str = Field(default="pdf", pattern="^(pdf|html|markdown|json)$")
    include_ai: bool = True


class ExportCreateRequest(BaseModel):
    entity_type: str = Field(..., pattern="^(investigation|evidence|report|graph|timeline)$")
    entity_id: uuid.UUID
    format: str = Field(..., pattern="^(pdf|html|markdown|json|csv|zip)$")
    workspace_id: uuid.UUID


class ExportJobResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    format: str
    status: str
    file_size: int | None = None
    download_token: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    notification_type: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool = False
    read_at: datetime | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ActivityEventResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID | None = None
    actor_id: uuid.UUID
    event_type: str
    title: str
    description: str | None = None
    metadata_json: dict | None = None
    occurred_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MemberActivityResponse(BaseModel):
    id: uuid.UUID
    display_name: str | None = None
    email: str = ""
    event_count: int = 0


class WorkspaceDashboardResponse(BaseModel):
    total_investigations: int = 0
    open_investigations: int = 0
    in_progress_investigations: int = 0
    closed_investigations: int = 0
    total_evidence: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    total_timeline_events: int = 0
    recent_activity: list[ActivityEventResponse] = Field(default_factory=list)
    top_investigators: list[MemberActivityResponse] = Field(default_factory=list)


class EvidenceAnalyticsResponse(BaseModel):
    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    total_storage_bytes: int = 0
    evidence_per_day: dict[str, int] = Field(default_factory=dict)
    recent_uploads: int = 0


class GlobalSearchResult(BaseModel):
    id: str
    type: str
    title: str
    description: str | None = None
    match_field: str | None = None
    score: float = 0.0
    link: str = ""
    workspace_id: str | None = None


class GlobalSearchResponse(BaseModel):
    results: list[GlobalSearchResult] = Field(default_factory=list)
    total: int = 0
    query: str = ""
    skip: int = 0
    limit: int = 50
