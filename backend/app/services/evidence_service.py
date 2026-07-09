"""
Evidence service — core business logic for evidence management.

Handles CRUD, upload, download, verification, versioning, search, tags, and comments.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.evidence import Evidence, EvidenceStatus
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


class EvidenceService:
    """Business logic for evidence operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BaseRepository(db, Evidence)
        self.custody = CustodyService(db)
        self._storage: StorageProvider | None = None

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

    async def _check_project_belongs_to_workspace(self, project_id: uuid.UUID, workspace_id: Optional[uuid.UUID] = None) -> Project:
        proj_repo = BaseRepository(self.db, Project)
        proj = await proj_repo.get(project_id)
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if workspace_id is not None and proj.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace")
        return proj

    def _generate_evidence_number(self) -> str:
        prefix = "ET"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
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

        await self.db.commit()
        await self.db.refresh(evidence)

        await self.custody.record(evidence.id, user_id, "create",
                                  notes=f"Evidence '{evidence.title}' created")
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

        await self.db.commit()
        if changed:
            await self.custody.record(ev.id, user_id, "update",
                                      notes=f"Fields updated: {', '.join(changed)}")
        await self.db.refresh(ev)
        return ev

    async def delete(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> None:
        ev = await self.get(evidence_id, user_id)
        ws_role = await self._check_member(ev.workspace_id, user_id)
        if ws_role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.INVESTIGATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        ev.is_deleted = True
        ev.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.custody.record(ev.id, user_id, "delete",
                                  notes=f"Evidence '{ev.title}' deleted")

    async def restore(self, evidence_id: uuid.UUID, user_id: uuid.UUID) -> Evidence:
        ev = await self.repo.get(evidence_id)
        if not ev or not ev.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted evidence not found")
        await self._check_member(ev.workspace_id, user_id)

        ev.is_deleted = False
        ev.deleted_at = None
        await self.db.commit()
        await self.db.refresh(ev)
        await self.custody.record(ev.id, user_id, "restore",
                                  notes=f"Evidence '{ev.title}' restored")
        return ev

    # ── File Upload ─────────────────────────────────────────────────────

    async def upload_file(self, evidence_id: uuid.UUID, file: UploadFile, user_id: uuid.UUID,
                          change_notes: Optional[str] = None) -> Evidence:
        ev = await self.get(evidence_id, user_id)

        # Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB")

        # Compute hashes
        content = await file.read()
        sha256 = hashlib.sha256(content).hexdigest()
        sha1 = hashlib.sha1(content).hexdigest()
        md5 = hashlib.md5(content).hexdigest()

        # Duplicate detection
        existing = await self.repo.find_one(sha256_hash=sha256)
        if existing and existing.id != evidence_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Duplicate file detected (SHA256: {sha256[:16]}...) already exists as evidence {existing.evidence_number}")

        # Store file
        mime = file.content_type or "application/octet-stream"
        stored = await self.storage.store(content, file.filename or "unnamed", mime)

        # Update evidence record
        ev.sha256_hash = sha256
        ev.sha1_hash = sha1
        ev.md5_hash = md5
        ev.mime_type = mime
        ev.file_size = size
        ev.original_filename = file.filename
        ev.stored_filename = stored.filename
        ev.storage_path = stored.path
        ev.upload_timestamp = datetime.now(timezone.utc)
        ev.current_version_number += 1

        # Create version record
        version = EvidenceVersion(
            evidence_id=ev.id,
            version_number=ev.current_version_number,
            created_by=user_id,
            original_filename=file.filename,
            stored_filename=stored.filename,
            storage_path=stored.path,
            mime_type=mime,
            file_size=size,
            sha256_hash=sha256,
            sha1_hash=sha1,
            md5_hash=md5,
            change_notes=change_notes,
        )
        self.db.add(version)
        await self.db.commit()

        await self.custody.record(ev.id, user_id, "upload",
                                  notes=f"File uploaded: {file.filename} ({size} bytes)",
                                  details=f"sha256={sha256}")
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
        return data, ev.original_filename or "download", ev.mime_type or "application/octet-stream"

    # ── Hash Verification ───────────────────────────────────────────────

    async def verify_hashes(self, evidence_id: uuid.UUID, user_id: uuid.UUID,
                            sha256: Optional[str] = None, sha1: Optional[str] = None,
                            md5: Optional[str] = None) -> dict[str, Any]:
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

        ev.verification_timestamp = datetime.now(timezone.utc)
        await self.db.commit()

        await self.custody.record(ev.id, user_id, "verify",
                                  notes=f"Hash verification: {'passed' if results['verified'] else 'FAILED'}",
                                  details=str(results))
        return results

    # ── List / Search ──────────────────────────────────────────────────

    async def list_for_project(self, project_id: uuid.UUID, user_id: uuid.UUID,
                                skip: int = 0, limit: int = 50) -> list[dict]:
        ev_list = await self.repo.find_many(project_id=project_id, is_deleted=False,
                                              order_by="created_at", descending=True,
                                              skip=skip, limit=limit)
        result = []
        for ev in ev_list:
            tags = await self._get_tag_names(ev.id)
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
            for tag in tag_list:
                query = query.where(
                    Evidence.id.in_(select(EvidenceTag.evidence_id).where(EvidenceTag.tag == tag))
                )

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

        items = []
        for ev in ev_list:
            tags = await self._get_tag_names(ev.id)
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

        total = await self.repo.count(project_id=project_id, is_deleted=False)

        # Per status
        status_counts = {}
        for s in EvidenceStatus:
            cnt = await self.repo.count(project_id=project_id, is_deleted=False, status=s)
            if cnt > 0:
                status_counts[s.value] = cnt

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

        # Total size
        size_result = await self.db.execute(
            select(func.coalesce(func.sum(Evidence.file_size), 0)).where(
                Evidence.project_id == project_id, Evidence.is_deleted == False,
            )
        )
        total_size = size_result.scalar() or 0

        # Recent uploads (last 7 days)
        from datetime import timedelta
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
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
        comment.edited_at = datetime.now(timezone.utc)
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

    async def bulk_action(self, evidence_ids: list[uuid.UUID], action: str, user_id: uuid.UUID) -> dict:
        results = {"affected": 0, "errors": []}
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
