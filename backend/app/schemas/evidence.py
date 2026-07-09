"""Evidence schemas — request and response models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.evidence import EvidencePriority, EvidenceStatus


class EvidenceCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    category: str = Field(default="other", max_length=100)
    priority: EvidencePriority = EvidencePriority.MEDIUM
    source: str | None = Field(None, max_length=255)
    collector_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)


class EvidenceUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    category: str | None = Field(None, max_length=100)
    priority: EvidencePriority | None = None
    status: EvidenceStatus | None = None
    source: str | None = Field(None, max_length=255)
    collector_id: uuid.UUID | None = None
    tags: list[str] | None = None


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    collector_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    evidence_number: str
    category: str
    status: EvidenceStatus
    priority: EvidencePriority
    source: str | None = None
    sha256_hash: str | None = None
    sha1_hash: str | None = None
    md5_hash: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    original_filename: str | None = None
    stored_filename: str | None = None
    upload_timestamp: datetime | None = None
    verification_timestamp: datetime | None = None
    current_version_number: int = 1
    is_deleted: bool = False
    tags: list[str] = Field(default_factory=list)
    comment_count: int = 0
    version_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    evidence_number: str
    category: str
    status: EvidenceStatus
    priority: EvidencePriority
    sha256_hash: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    original_filename: str | None = None
    tag_names: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSearchParams(BaseModel):
    query: str | None = Field(None, max_length=500)
    project_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    category: str | None = None
    status: EvidenceStatus | None = None
    priority: EvidencePriority | None = None
    tags: list[str] | None = None
    collector_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    hash_value: str | None = None
    filename: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: str = "created_at"
    sort_desc: bool = True


class EvidenceStats(BaseModel):
    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    total_size_bytes: int = 0
    recent_uploads: int = 0


class EvidenceVersionResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    version_number: int
    created_by: uuid.UUID
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    sha256_hash: str | None = None
    change_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


class EvidenceCommentUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


class EvidenceCommentResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceUploadResponse(BaseModel):
    evidence: EvidenceResponse
    custody_event: CustodyEventResponse | None = None


class CustodyEventResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    timestamp: datetime
    ip_address: str | None = None
    request_id: str | None = None
    notes: str | None = None
    details: str | None = None

    model_config = {"from_attributes": True}


class BulkActionRequest(BaseModel):
    evidence_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(delete|restore|archive|verify|update_status)$")


class VerifyRequest(BaseModel):
    sha256_hash: str | None = None
    sha1_hash: str | None = None
    md5_hash: str | None = None
