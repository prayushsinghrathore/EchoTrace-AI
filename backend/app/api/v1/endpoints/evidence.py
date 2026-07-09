"""Evidence API endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.evidence import (
    BulkActionRequest,
    CustodyEventResponse,
    EvidenceCommentCreate,
    EvidenceCommentResponse,
    EvidenceCommentUpdate,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceStats,
    EvidenceUpdate,
    EvidenceVersionResponse,
    VerifyRequest,
)
from app.services.custody_service import CustodyService
from app.services.evidence_service import EvidenceService

router = APIRouter(tags=["evidence"])


def _enrich_evidence(ev, tags=None, comment_count=0, version_count=0):
    """Convert evidence model to response dict."""
    return {
        "id": ev.id,
        "project_id": ev.project_id,
        "workspace_id": ev.workspace_id,
        "created_by": ev.created_by,
        "collector_id": ev.collector_id,
        "title": ev.title,
        "description": ev.description,
        "evidence_number": ev.evidence_number,
        "category": ev.category,
        "status": ev.status.value if hasattr(ev.status, "value") else ev.status,
        "priority": ev.priority.value if hasattr(ev.priority, "value") else ev.priority,
        "source": ev.source,
        "sha256_hash": ev.sha256_hash,
        "sha1_hash": ev.sha1_hash,
        "md5_hash": ev.md5_hash,
        "mime_type": ev.mime_type,
        "file_size": ev.file_size,
        "original_filename": ev.original_filename,
        "stored_filename": ev.stored_filename,
        "upload_timestamp": ev.upload_timestamp,
        "verification_timestamp": ev.verification_timestamp,
        "current_version_number": ev.current_version_number,
        "is_deleted": ev.is_deleted,
        "tags": tags or [],
        "comment_count": comment_count,
        "version_count": version_count,
        "created_at": ev.created_at,
        "updated_at": ev.updated_at,
    }


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    body: EvidenceCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    ev = await svc.create(
        project_id=body.project_id,
        user_id=user.id,
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
        source=body.source,
        collector_id=body.collector_id,
        tags=body.tags,
    )
    return _enrich_evidence(ev, tags=body.tags)


@router.get("", response_model=list)
async def list_evidence(
    project_id: uuid.UUID = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.list_for_project(project_id, user.id, skip=skip, limit=limit)


@router.get("/search", response_model=dict)
async def search_evidence(
    q: Optional[str] = Query(None, max_length=500),
    project_id: Optional[uuid.UUID] = Query(None),
    workspace_id: Optional[uuid.UUID] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    hash_value: Optional[str] = Query(None),
    filename: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_desc: bool = Query(True),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    params = {
        "query": q, "project_id": project_id, "workspace_id": workspace_id,
        "category": category, "status": status, "priority": priority,
        "hash_value": hash_value, "filename": filename,
        "skip": skip, "limit": limit, "sort_by": sort_by, "sort_desc": sort_desc,
    }
    items, total = await svc.search(params, user.id)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    ev = await svc.get(evidence_id, user.id)
    tags = await svc._get_tag_names(ev.id)
    return _enrich_evidence(ev, tags=tags)


@router.patch("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: uuid.UUID,
    body: EvidenceUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    ev = await svc.update(evidence_id, user.id, **body.model_dump(exclude_none=True))
    tags = await svc._get_tag_names(ev.id)
    return _enrich_evidence(ev, tags=tags)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    await svc.delete(evidence_id, user.id)


@router.post("/{evidence_id}/restore", response_model=EvidenceResponse)
async def restore_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    ev = await svc.restore(evidence_id, user.id)
    return _enrich_evidence(ev)


@router.post("/{evidence_id}/upload", response_model=EvidenceResponse)
async def upload_file(
    evidence_id: uuid.UUID,
    file: UploadFile = File(...),
    change_notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    ev = await svc.upload_file(evidence_id, file, user.id, change_notes=change_notes)
    tags = await svc._get_tag_names(ev.id)
    return _enrich_evidence(ev, tags=tags)


@router.get("/{evidence_id}/download")
async def download_file(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    data, filename, mime = await svc.download_file(evidence_id, user.id)
    return StreamingResponse(iter([data]), media_type=mime,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/{evidence_id}/verify", response_model=dict)
async def verify_evidence(
    evidence_id: uuid.UUID,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.verify_hashes(evidence_id, user.id,
                                    sha256=body.sha256_hash, sha1=body.sha1_hash, md5=body.md5_hash)


# ── Versions ───────────────────────────────────────────────────────────────

@router.get("/{evidence_id}/versions", response_model=list[EvidenceVersionResponse])
async def list_versions(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.list_versions(evidence_id, user.id)


@router.get("/versions/{version_id}", response_model=EvidenceVersionResponse)
async def get_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.get_version(version_id, user.id)


# ── Comments ───────────────────────────────────────────────────────────────

@router.get("/{evidence_id}/comments", response_model=list[EvidenceCommentResponse])
async def list_comments(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.list_comments(evidence_id, user.id)


@router.post("/{evidence_id}/comments", response_model=EvidenceCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    evidence_id: uuid.UUID,
    body: EvidenceCommentCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.add_comment(evidence_id, user.id, body.body)


@router.patch("/comments/{comment_id}", response_model=EvidenceCommentResponse)
async def edit_comment(
    comment_id: uuid.UUID,
    body: EvidenceCommentUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.edit_comment(comment_id, user.id, body.body)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    await svc.delete_comment(comment_id, user.id)


# ── Chain of Custody ───────────────────────────────────────────────────────

@router.get("/{evidence_id}/custody", response_model=list[CustodyEventResponse])
async def list_custody(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = CustodyService(db)
    return await svc.list_for_evidence(evidence_id)


# ── Statistics ─────────────────────────────────────────────────────────────

@router.get("/stats/project/{project_id}", response_model=EvidenceStats)
async def evidence_stats(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.get_stats(project_id, user.id)


# ── Bulk Actions ───────────────────────────────────────────────────────────

@router.post("/bulk", response_model=dict)
async def bulk_action(
    body: BulkActionRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    svc = EvidenceService(db)
    return await svc.bulk_action(body.evidence_ids, body.action, user.id)
