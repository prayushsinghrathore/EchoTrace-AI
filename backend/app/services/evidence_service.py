"""Evidence service — core business logic for evidence management.

Handles CRUD, upload, download, verification, versioning, search, tags, and comments.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import sanitize_filename
from app.models.evidence import Evidence
from app.models.evidence_comment import EvidenceComment
from app.models.evidence_tag import EvidenceTag
from app.models.evidence_version import EvidenceVersion
from app.models.project import Project
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository
from app.services.custody_service import CustodyService
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider

logger = get_logger(__name__)

# Common file magic bytes for server-side content-type validation
# (bytes, offset, MIME type)
_MIME_MAGIC_BYTES: list[tuple[bytes, int, str]] = [
    (b"\x89PNG\r\n\x1a\n", 0, "image/png"),
    (b"\xff\xd8\xff", 0, "image/jpeg"),
    (b"GIF87a", 0, "image/gif"),
    (b"GIF89a", 0, "image/gif"),
    (b"RIFF", 0, "image/webp"),        # WEBP header
    (b"%PDF", 0, "application/pdf"),
    (b"PK\x03\x04", 0, "application/zip"),
    (b"\x1f\x8b\x08", 0, "application/gzip"),
    (b"ustar\x00", 257, "application/x-tar"),
    (b"Rar!\x1a\x07\x00", 0, "application/x-rar-compressed"),
    (b"\x00\x00\x00\x18ftypmp42", 0, "video/mp4"),
    (b"\x00\x00\x00\x1cftypmp42", 0, "video/mp4"),
    (b"\x00\x00\x00 ftypisom", 0, "video/mp4"),
    (b"\x1aE\xdf\xa3", 0, "video/x-matroska"),  # MKV
    (b"ID3", 0, "audio/mpeg"),
    (b"\xff\xfb", 0, "audio/mpeg"),
    (b"\xff\xf3", 0, "audio/mpeg"),
    (b"OggS", 0, "audio/ogg"),
    (b"RIFF", 0, "audio/wav"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, "application/vnd.ms-excel"),   # OLE2 (xls/doc/ppt)
    (b"Microsoft Office", 0, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),  # Approximate
]


def _detect_mime_from_magic(content: bytes) -> str | None:
    """Detect MIME type from file magic bytes.

    Returns None if no magic signature matches.
    """
    for signature, offset, mime in _MIME_MAGIC_BYTES:
        if len(content) >= offset + len(signature) and content[offset : offset + len(signature)] == signature:
                return mime
    return None


class EvidenceService:
    """Business logic for evidence operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Evidence)
        self.custody = CustodyService(db)
        self._storage: StorageProvider | None = None
        self._upload_semaphore = asyncio.Semaphore(settings.UPLOAD_CONCURRENCY_LIMIT)

    @property
    def storage(self) -> StorageProvider:
        if self._storage is None:
            self._storage = LocalStorageProvider()
        return self._storage

    async def _check_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceRole:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        return member.role

    async def _check_project_belongs_to_workspace(self, project_id: uuid.UUID, workspace_id: uuid.UUID | None = None) -> Project:
        proj_repo = BaseRepository(self.db, Project)
        proj = await proj_repo.get(project_id)
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if workspace_id is not None and proj.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace")
        return proj

    def _generate_evidence_number(self) -> str:
        prefix = "ET"
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        rand = secrets.token_hex(4).upper()
        return f"{prefix}-{ts}-{rand}"

    async def _sync_tags(self, evidence: Evidence, tags: list[str]) -> None:
        """Replace all tags on evidence with the provided list."""
        await self.db.execute(
            sa_delete(EvidenceTag).where(EvidenceTag.evidence_id == evidence.id)
        )
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if tag_name:
                self.db.add(EvidenceTag(evidence_id=evidence.id, tag=tag_name))

    async def _get_tag_names(self, evidence_id: uuid.UUID) -> list[str]:
        tag_repo = BaseRepository(self.db, EvidenceTag)
        tags = await tag_repo.find_many(evidence_id=evidence_id)
        return [t.tag for t in tags]

    async def _batch_load_tags(self, evidence_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
        """Load tags for multiple evidence items in a single query.

        Returns a dict mapping evidence_id -> [tag_names].
        Eliminates N+1 queries when listing/searching evidence.
        """
        if not evidence_ids:
            return {}
        stmt = select(EvidenceTag).where(EvidenceTag.evidence_id.in_(evidence_ids))
        result = await self.db.execute(stmt)
        tag_rows = list(result.scalars().all())
        tag_map: dict[uuid.UUID, list[str]] = {eid: [] for eid in evidence_ids}
        for tag in tag_rows:
            tag_map.setdefault(tag.evidence_id, []).append(tag.tag)
        return tag_map

    async def create(self, project_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Evidence:
        proj = await self._check_project_belongs_to_workspace(project_id)
        workspace_id = proj.workspace_id
        ws_role = await self._check_member(workspace_id, user_id)
        if ws_role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to create evidence")

        tags = kwargs.pop("tags", [])

        evidence = Evidence(
            project_id=project_id,
            workspace_id=workspace_id,
            created_by=user_id,
            evidence_number=self._generate_evidence_number(),
            **kwargs,
        )
        self.db.add(evidence)
        await self.db.flush()

        if tags:
            await self._sync_tags(evidence, tags)

        await self.custody.record(evidence.id, user_id, "create",
                                  notes=f"Evidence '{evidence.title}' created")
        await self.db.commit()
        await self.db.refresh(evidence)
        logger.info("Evidence created", ev_id=str(evidence.id), num=evidence.evidence_number)
        return evidence

    async def get(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> Evidence:
        ev = await self.repo.get(evidence_id)
        if not ev or ev.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
        await self._check_member(ev.workspace_id, user_id)
        return ev

    async def update(self, evidence_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Evidence:
        ev = await self.get(evidence_id, user_id)
        ws_role = await self._check_member(ev.workspace_id, user_id)
        if ws_role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        tags = kwargs.pop("tags", None)
        changed = []

        for key, val in kwargs.items():
            if val is not None and hasattr(ev, key):
                old = getattr(ev, key)
                if old != val:
                    setattr(ev, key, val)
                    changed.append(key)

        if tags is not None:
            await self._sync_tags(ev, tags)
            changed.append("tags")

        if changed:
            await self.custody.record(ev.id, user_id, "update",
                                      notes=f"Fields updated: {', '.join(changed)}")
        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    async def delete(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> None:
        ev = await self.get(evidence_id, user_id)
        ws_role = await self._check_member(ev.workspace_id, user_id)
        if ws_role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        ev.is_deleted = True
        ev.deleted_at = datetime.now(UTC)
        await self.custody.record(ev.id, user_id, "delete",
                                  notes=f"Evidence '{ev.title}' deleted")
        await self.db.commit()

    async def restore(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> Evidence:
        ev = await self.repo.get(evidence_id)
        if not ev or not ev.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted evidence not found")
        await self._check_member(ev.workspace_id, user_id)

        ev.is_deleted = False
        ev.deleted_at = None
        await self.custody.record(ev.id, user_id, "restore",
                                  notes=f"Evidence '{ev.title}' restored")
        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    # ── File Upload ─────────────────────────────────────────────────────

    async def upload_file(self, evidence_id: uuid.UUID, file: UploadFile, user_id: uuid.UUID,
                          change_notes: str | None = None) -> Evidence:
        ev = await self.get(evidence_id, user_id)

        # Enforce concurrent upload limit (memory guard)
        async with self._upload_semaphore:
            # Validate file size
            max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
            if size > max_bytes:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                    detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB")
            if size == 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Uploaded file is empty")

            # Compute hashes
            content = await file.read()

            # Server-side MIME type detection via magic bytes
            detected_mime = _detect_mime_from_magic(content)
            declared_mime = (file.content_type or "application/octet-stream").lower()

            # Resolve MIME: prefer magic byte detection over client declaration
            resolved_mime = detected_mime or declared_mime

            # Validate against allowed MIME types
            if resolved_mime not in settings.ALLOWED_MIME_TYPES:
                logger.warning(
                    "Upload rejected — invalid MIME type",
                    declared=declared_mime,
                    detected=detected_mime,
                    filename=file.filename,
                )
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"File type '{resolved_mime}' is not allowed. "
                           f"Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES[:10])}",
                )

            # If magic bytes detected a different type than declared, log it
            if detected_mime and declared_mime not in (detected_mime, "application/octet-stream"):
                logger.warning(
                    "MIME type mismatch",
                    declared=declared_mime,
                    detected=detected_mime,
                    filename=file.filename,
                )

            sha256 = hashlib.sha256(content).hexdigest()
            sha1 = hashlib.sha1(content).hexdigest()
            md5 = hashlib.md5(content).hexdigest()

            # Duplicate detection
            existing = await self.repo.find_one(sha256_hash=sha256)
            if existing and existing.id != evidence_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Duplicate file detected (SHA256: {sha256[:16]}...) already exists as evidence {existing.evidence_number}")

            # Sanitize filename
            safe_filename = sanitize_filename(file.filename or "unnamed")

            # Store file with detected MIME
            stored = await self.storage.store(content, safe_filename, resolved_mime)

            # Update evidence record
            ev.sha256_hash = sha256
            ev.sha1_hash = sha1
            ev.md5_hash = md5
            ev.mime_type = resolved_mime
            ev.file_size = size
            ev.original_filename = safe_filename
            ev.stored_filename = stored.filename
            ev.storage_path = stored.path
            ev.upload_timestamp = datetime.now(UTC)
            ev.current_version_number += 1

            # Create version record
            version = EvidenceVersion(
                evidence_id=ev.id,
                version_number=ev.current_version_number,
                created_by=user_id,
                original_filename=safe_filename,
                stored_filename=stored.filename,
                storage_path=stored.path,
                mime_type=resolved_mime,
                file_size=size,
                sha256_hash=sha256,
                sha1_hash=sha1,
                md5_hash=md5,
                change_notes=change_notes,
            )
            self.db.add(version)
            await self.db.flush()

            await self.custody.record(ev.id, user_id, "upload",
                                      notes=f"File uploaded: {safe_filename} ({size} bytes)",
                                      details=f"sha256={sha256}")
            await self.db.commit()
            await self.db.refresh(ev)
            return ev

    # ── Download ────────────────────────────────────────────────────────

    async def download_file(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> tuple[bytes, str, str]:
        ev = await self.get(evidence_id, user_id)
        if not ev.storage_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file stored for this evidence")

        data = await self.storage.retrieve(ev.storage_path)
        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on storage")

        await self.custody.record(ev.id, user_id, "download",
                                  notes=f"File downloaded: {ev.original_filename}")
        await self.db.commit()
        return data, ev.original_filename or "download", ev.mime_type or "application/octet-stream"

    # ── Hash Verification ───────────────────────────────────────────────

    async def verify_hashes(self, evidence_id: uuid.UUID, user_id: uuid.UUID,
                            sha256: str | None = None, sha1: str | None = None,
                            md5: str | None = None) -> dict[str, Any]:
        ev = await self.get(evidence_id, user_id)
        results: dict[str, Any] = {"verified": True, "checks": {}}

        if sha256:
            match = ev.sha256_hash == sha256.lower()
            results["checks"]["sha256"] = {"expected": ev.sha256_hash, "provided": sha256, "match": match}
            if not match:
                results["verified"] = False

        if sha1:
            match = ev.sha1_hash == sha1.lower()
            results["checks"]["sha1"] = {"expected": ev.sha1_hash, "provided": sha1, "match": match}
            if not match:
                results["verified"] = False

        if md5:
            match = ev.md5_hash == md5.lower()
            results["checks"]["md5"] = {"expected": ev.md5_hash, "provided": md5, "match": match}
            if not match:
                results["verified"] = False

        ev.verification_timestamp = datetime.now(UTC)
        await self.custody.record(ev.id, user_id, "verify",
                                  notes=f"Hash verification: {'passed' if results['verified'] else 'FAILED'}",
                                  details=str(results))
        await self.db.commit()
        return results

    # ── List / Search ──────────────────────────────────────────────────

    async def list_for_project(self, project_id: uuid.UUID, _user_id: uuid.UUID,
                                skip: int = 0, limit: int = 50) -> list[dict]:
        ev_list = await self.repo.find_many(project_id=project_id, is_deleted=False,
                                              order_by="created_at", descending=True,
                                              skip=skip, limit=limit)
        # Batch-load tags for all evidence items (eliminates N+1)
        tag_map = await self._batch_load_tags([ev.id for ev in ev_list])
        result = []
        for ev in ev_list:
            tags = tag_map.get(ev.id, [])
            result.append({
                "id": ev.id,
                "project_id": ev.project_id,
                "title": ev.title,
                "evidence_number": ev.evidence_number,
                "category": ev.category,
                "status": ev.status.value if hasattr(ev.status, 'value') else ev.status,
                "priority": ev.priority.value if hasattr(ev.priority, 'value') else ev.priority,
                "sha256_hash": ev.sha256_hash,
                "mime_type": ev.mime_type,
                "file_size": ev.file_size,
                "original_filename": ev.original_filename,
                "tag_names": tags,
                "created_at": ev.created_at,
            })
        return result

    async def count_for_project(self, project_id: uuid.UUID) -> int:
        return await self.repo.count(project_id=project_id, is_deleted=False)

    # ── Search ──────────────────────────────────────────────────────────

    async def search(self, params: dict, user_id: uuid.UUID) -> tuple[list[dict], int]:
        """Full-text and filtered search with pagination."""
        query = select(Evidence).where(Evidence.is_deleted == False)

        # Member access filter
        subq = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        query = query.where(Evidence.workspace_id.in_(subq))

        if params.get("query"):
            q = f"%{params['query']}%"
            query = query.where(
                or_(Evidence.title.ilike(q), Evidence.description.ilike(q),
                    Evidence.evidence_number.ilike(q), Evidence.original_filename.ilike(q))
            )
        if params.get("project_id"):
            query = query.where(Evidence.project_id == params["project_id"])
        if params.get("workspace_id"):
            query = query.where(Evidence.workspace_id == params["workspace_id"])
        if params.get("category"):
            query = query.where(Evidence.category == params["category"])
        if params.get("status"):
            query = query.where(Evidence.status == params["status"])
        if params.get("priority"):
            query = query.where(Evidence.priority == params["priority"])
        if params.get("collector_id"):
            query = query.where(Evidence.collector_id == params["collector_id"])
        if params.get("created_by"):
            query = query.where(Evidence.created_by == params["created_by"])
        if params.get("hash_value"):
            hv = params["hash_value"].lower()
            query = query.where(
                or_(Evidence.sha256_hash == hv, Evidence.sha1_hash == hv, Evidence.md5_hash == hv)
            )
        if params.get("filename"):
            query = query.where(Evidence.original_filename.ilike(f"%{params['filename']}%"))
        if params.get("date_from"):
            query = query.where(Evidence.created_at >= params["date_from"])
        if params.get("date_to"):
            query = query.where(Evidence.created_at <= params["date_to"])
        if params.get("tags"):
            tag_list = params["tags"]
            # Single EXISTS clause matching all required tags (eliminates N correlated subqueries)
            for tag in tag_list:
                tag_subq = select(EvidenceTag.evidence_id).where(
                    EvidenceTag.tag == tag,
                    EvidenceTag.evidence_id == Evidence.id,
                ).correlate(Evidence).exists()
                query = query.where(tag_subq)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Sort
        sort_col = getattr(Evidence, params.get("sort_by", "created_at"), Evidence.created_at)
        if params.get("sort_desc", True):
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        query = query.offset(params.get("skip", 0)).limit(params.get("limit", 50))
        result = await self.db.execute(query)
        ev_list = list(result.scalars().all())

        # Batch-load tags for all evidence items (eliminates N+1)
        tag_map = await self._batch_load_tags([ev.id for ev in ev_list])
        items = []
        for ev in ev_list:
            tags = tag_map.get(ev.id, [])
            items.append({
                "id": ev.id,
                "project_id": ev.project_id,
                "workspace_id": ev.workspace_id,
                "title": ev.title,
                "evidence_number": ev.evidence_number,
                "category": ev.category,
                "status": ev.status.value if hasattr(ev.status, 'value') else ev.status,
                "priority": ev.priority.value if hasattr(ev.priority, 'value') else ev.priority,
                "sha256_hash": ev.sha256_hash,
                "mime_type": ev.mime_type,
                "file_size": ev.file_size,
                "original_filename": ev.original_filename,
                "tag_names": tags,
                "created_by": str(ev.created_by),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })
        return items, total

    # ── Statistics ──────────────────────────────────────────────────────

    async def get_stats(self, project_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        await self._check_project_belongs_to_workspace(project_id, None)
        del user_id

        # Single aggregated stats query replacing 6 sequential per-status queries
        base_filters = (Evidence.project_id == project_id, Evidence.is_deleted == False)

        agg_query = select(
            func.count(Evidence.id).label("total"),
            func.coalesce(func.sum(Evidence.file_size), 0).label("total_size"),
        ).where(*base_filters)
        agg_result = await self.db.execute(agg_query)
        agg_row = agg_result.one()
        total = agg_row.total
        total_size = agg_row.total_size

        # Per status (single GROUP BY query instead of 6 separate count queries)
        status_query = select(
            Evidence.status, func.count(Evidence.id)
        ).where(*base_filters).group_by(Evidence.status)
        status_result = await self.db.execute(status_query)
        status_counts = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in status_result}

        # Per category
        cat_query = select(Evidence.category, func.count(Evidence.id)).where(
            Evidence.project_id == project_id, Evidence.is_deleted == False,
        ).group_by(Evidence.category)
        cat_result = await self.db.execute(cat_query)
        by_category = {row[0]: row[1] for row in cat_result}

        # Per priority
        pri_query = select(Evidence.priority, func.count(Evidence.id)).where(
            Evidence.project_id == project_id, Evidence.is_deleted == False,
        ).group_by(Evidence.priority)
        pri_result = await self.db.execute(pri_query)
        by_priority = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in pri_result}

        # Recent uploads (last 7 days)
        from datetime import timedelta
        week_ago = datetime.now(UTC) - timedelta(days=7)
        recent_result = await self.db.execute(
            select(func.count(Evidence.id)).where(
                Evidence.project_id == project_id, Evidence.is_deleted == False,
                Evidence.upload_timestamp >= week_ago,
            )
        )
        recent = recent_result.scalar() or 0

        return {
            "total": total,
            "by_status": status_counts,
            "by_category": by_category,
            "by_priority": by_priority,
            "total_size_bytes": total_size,
            "recent_uploads": recent,
        }

    # ── Versioning ──────────────────────────────────────────────────────

    async def list_versions(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> list[EvidenceVersion]:
        ev = await self.get(evidence_id, user_id)
        ver_repo = BaseRepository(self.db, EvidenceVersion)
        versions = await ver_repo.find_many(evidence_id=ev.id, order_by="version_number", descending=True)
        return versions

    async def get_version(self, version_id: uuid.UUID, user_id: uuid.UUID) -> EvidenceVersion:
        ver_repo = BaseRepository(self.db, EvidenceVersion)
        ver = await ver_repo.get(version_id)
        if not ver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        ev = await self.repo.get(ver.evidence_id)
        if not ev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
        await self._check_member(ev.workspace_id, user_id)
        return ver

    # ── Comments ────────────────────────────────────────────────────────

    async def add_comment(self, evidence_id: uuid.UUID, user_id: uuid.UUID, body: str) -> EvidenceComment:
        await self.get(evidence_id, user_id)
        comment = EvidenceComment(evidence_id=evidence_id, author_id=user_id, body=body)
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def edit_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID, body: str) -> EvidenceComment:
        comment_repo = BaseRepository(self.db, EvidenceComment)
        comment = await comment_repo.get(comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        if comment.author_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only edit own comments")
        comment.body = body
        comment.is_edited = True
        comment.edited_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID) -> None:
        comment_repo = BaseRepository(self.db, EvidenceComment)
        comment = await comment_repo.get(comment_id)
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        if comment.author_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete own comments")
        await comment_repo.delete(comment_id, hard=True)
        await self.db.commit()

    async def list_comments(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> list[EvidenceComment]:
        await self.get(evidence_id, user_id)
        comment_repo = BaseRepository(self.db, EvidenceComment)
        return await comment_repo.find_many(evidence_id=evidence_id, order_by="created_at", descending=True)

    async def bulk_action(self, evidence_ids: list[uuid.UUID], action: str, user_id: uuid.UUID) -> dict[str, Any]:
        results: dict[str, Any] = {"affected": 0, "errors": []}
        for ev_id in evidence_ids:
            try:
                if action == "delete":
                    await self.delete(ev_id, user_id)
                elif action == "restore":
                    await self.restore(ev_id, user_id)
                elif action == "verify":
                    await self.verify_hashes(ev_id, user_id, None, None, None)
                results["affected"] += 1
            except HTTPException as exc:
                results["errors"].append({"evidence_id": str(ev_id), "error": exc.detail})
        if results["errors"]:
            results["status"] = "partial"
        else:
            results["status"] = "completed"
        return results
