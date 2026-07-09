"""Evidence schemas — request and response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.evidence import EvidencePriority, EvidenceStatus


class EvidenceCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    category: str = Field(default="other", max_length=100)
    priority: EvidencePriority = EvidencePriority.MEDIUM
    source: Optional[str] = Field(None, max_length=255)
    collector_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list)


class EvidenceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    category: Optional[str] = Field(None, max_length=100)
    priority: Optional[EvidencePriority] = None
    status: Optional[EvidenceStatus] = None
    source: Optional[str] = Field(None, max_length=255)
    collector_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    collector_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    evidence_number: str
    category: str
    status: EvidenceStatus
    priority: EvidencePriority
    source: Optional[str] = None
    sha256_hash: Optional[str] = None
    sha1_hash: Optional[str] = None
    md5_hash: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    original_filename: Optional[str] = None
    stored_filename: Optional[str] = None
    upload_timestamp: Optional[datetime] = None
    verification_timestamp: Optional[datetime] = None
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
    sha256_hash: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    original_filename: Optional[str] = None
    tag_names: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSearchParams(BaseModel):
    query: Optional[str] = Field(None, max_length=500)
    project_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    status: Optional[EvidenceStatus] = None
    priority: Optional[EvidencePriority] = None
    tags: Optional[list[str]] = None
    collector_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    hash_value: Optional[str] = None
    filename: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
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
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    sha256_hash: Optional[str] = None
    change_notes: Optional[str] = None
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
    custody_event: Optional["CustodyEventResponse"] = None


class CustodyEventResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    timestamp: datetime
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    notes: Optional[str] = None
    details: Optional[str] = None

    model_config = {"from_attributes": True}


class BulkActionRequest(BaseModel):
    evidence_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(delete|restore|archive|verify|update_status)$")


class VerifyRequest(BaseModel):
    sha256_hash: Optional[str] = None
    sha1_hash: Optional[str] = None
    md5_hash: Optional[str] = None
