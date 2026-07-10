"""
Reports, Export, Notifications, Activity, and Analytics API endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func as sa_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.models.activity_event import ActivityEvent
from app.models.entity import Entity
from app.models.evidence import Evidence, EvidenceStatus
from app.models.investigation import Investigation, InvestigationStatus
from app.models.relationship import Relationship
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user import User as UserModel
from app.models.workspace_member import WorkspaceMember
from app.reports.generator import ReportGenerator
from app.reports.renderer import ReportRenderer
from app.reports.schemas import (
    ActivityEventResponse,
    EvidenceAnalyticsResponse,
    ExportCreateRequest,
    ExportJobResponse,
    GlobalSearchResponse,
    GlobalSearchResult,
    MemberActivityResponse,
    NotificationResponse,
    ReportGenerateRequest,
    WorkspaceDashboardResponse,
)
from app.repositories.base import BaseRepository
from app.services.activity_service import ActivityService
from app.services.export_service import ExportService
from app.services.notification_service import NotificationService

logger = get_logger(__name__)

router = APIRouter(tags=["reports"])


async def _check_workspace_member(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    member_repo = BaseRepository(db, WorkspaceMember)
    member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")


# ── Report Generation ────────────────────────────────────────────────────────


@router.post("/generate", response_model=dict)
async def generate_report(
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate an investigation report and return in the requested format."""
    gen = ReportGenerator(db)
    renderer = ReportRenderer()
    try:
        data = await gen.generate(
            investigation_id=body.investigation_id,
            user_id=user.id,
            include_ai=body.include_ai_findings,
            include_custody=body.include_custody,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if body.format == "html":
        content = renderer.render_html(data)
    elif body.format == "json":
        content = renderer.render_json(data)
    else:
        content = renderer.render_markdown(data)

    return {
        "title": data.metadata.title,
        "format": body.format,
        "content": content,
        "generated_at": data.metadata.generated_at.isoformat() if data.metadata.generated_at else "",
        "statistics": data.statistics,
    }


# ── Export System ─────────────────────────────────────────────────────────────


@router.post("/export", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ExportJobResponse:
    """Create a background export job."""
    svc = ExportService(db)
    job = await svc.create_export(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        fmt=body.format,
        workspace_id=body.workspace_id,
        user_id=user.id,
    )
    return ExportJobResponse.model_validate(job)


@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(
    workspace_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[ExportJobResponse]:
    """List export jobs for a workspace."""
    svc = ExportService(db)
    jobs = await svc.list_for_workspace(workspace_id, user.id, limit=limit)
    return [ExportJobResponse.model_validate(j) for j in jobs]


@router.get("/exports/{job_id}", response_model=ExportJobResponse)
async def get_export(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ExportJobResponse:
    """Get the status of an export job."""
    svc = ExportService(db)
    job = await svc.get_job(job_id, user.id)
    return ExportJobResponse.model_validate(job)


@router.get("/download/{token}")
async def download_export(
    token: str,
    db: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Download an exported file using a signed token."""
    svc = ExportService(db)
    filepath, filename = await svc.download_with_token(token)
    return FileResponse(filepath, filename=filename, media_type="application/octet-stream")


# ── Notifications ─────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=dict)
async def list_notifications(
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """List notifications for the current user."""
    svc = NotificationService(db)
    items, total = await svc.list_for_user(user.id, unread_only=unread_only, skip=skip, limit=limit)
    return {
        "items": [NotificationResponse.model_validate(n) for n in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/notifications/unread-count", response_model=dict)
async def unread_notification_count(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Get unread notification count."""
    svc = NotificationService(db)
    count = await svc.unread_count(user.id)
    return {"count": count}


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a single notification as read."""
    svc = NotificationService(db)
    n = await svc.mark_read(notification_id, user.id)
    return NotificationResponse.model_validate(n)


@router.post("/notifications/read-all", response_model=dict)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Mark all notifications as read."""
    svc = NotificationService(db)
    count = await svc.mark_all_read(user.id)
    return {"marked_read": count}


# ── Activity Feed ─────────────────────────────────────────────────────────────


@router.get("/activity", response_model=dict)
async def list_workspace_activity(
    workspace_id: uuid.UUID = Query(...),
    investigation_id: uuid.UUID | None = Query(None),
    event_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """List activity events for a workspace."""
    svc = ActivityService(db)
    items, total = await svc.list_for_workspace(
        workspace_id, user.id,
        investigation_id=investigation_id,
        event_type=event_type,
        skip=skip, limit=limit,
    )
    return {
        "items": [ActivityEventResponse.model_validate(e) for e in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/activity/investigation/{investigation_id}", response_model=dict)
async def list_investigation_activity(
    investigation_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """List activity events for a specific investigation."""
    svc = ActivityService(db)
    items, total = await svc.list_for_investigation(investigation_id, user.id, skip=skip, limit=limit)
    return {
        "items": [ActivityEventResponse.model_validate(e) for e in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ── Analytics / Dashboard ─────────────────────────────────────────────────────


@router.get("/analytics/workspace/{workspace_id}", response_model=WorkspaceDashboardResponse)
async def workspace_analytics(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> WorkspaceDashboardResponse:
    """Get analytics dashboard data for a workspace."""
    await _check_workspace_member(db, workspace_id, user.id)

    inv_repo = BaseRepository(db, Investigation)
    ev_repo = BaseRepository(db, Evidence)
    ent_repo = BaseRepository(db, Entity)
    rel_repo = BaseRepository(db, Relationship)
    tl_repo = BaseRepository(db, TimelineEvent)
    act_repo = BaseRepository(db, ActivityEvent)

    all_invs = await inv_repo.find_many(workspace_id=workspace_id)
    total_invs = len(all_invs)
    open_count = sum(1 for i in all_invs if i.status == InvestigationStatus.OPEN)
    in_progress_count = sum(1 for i in all_invs if i.status == InvestigationStatus.IN_PROGRESS)
    closed_count = sum(1 for i in all_invs if i.status == InvestigationStatus.CLOSED)

    total_evidence = await ev_repo.count(workspace_id=workspace_id, is_deleted=False)
    total_entities = 0
    total_relationships = 0
    total_timeline = 0
    for inv in all_invs:
        total_entities += await ent_repo.count(investigation_id=inv.id)
        total_relationships += await rel_repo.count(investigation_id=inv.id)
        total_timeline += await tl_repo.count(investigation_id=inv.id)

    recent_activity = await act_repo.find_many(
        workspace_id=workspace_id, order_by="occurred_at", descending=True, limit=10
    )

    # Top investigators
    stmt = (
        select(ActivityEvent.actor_id, sa_func.count(ActivityEvent.id).label("cnt"))
        .where(ActivityEvent.workspace_id == workspace_id)
        .group_by(ActivityEvent.actor_id)
        .order_by(sa_func.count(ActivityEvent.id).desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    top_rows = result.all()
    top_investigators = []
    for row in top_rows:
        u_result = await db.execute(select(UserModel).where(UserModel.id == row.actor_id))
        u = u_result.scalar_one_or_none()
        if u:
            top_investigators.append(MemberActivityResponse(
                id=u.id, display_name=u.display_name, email=u.email,
                event_count=row.cnt,
            ))

    return WorkspaceDashboardResponse(
        total_investigations=total_invs,
        open_investigations=open_count,
        in_progress_investigations=in_progress_count,
        closed_investigations=closed_count,
        total_evidence=total_evidence,
        total_entities=total_entities,
        total_relationships=total_relationships,
        total_timeline_events=total_timeline,
        recent_activity=[ActivityEventResponse.model_validate(a) for a in recent_activity],
        top_investigators=top_investigators,
    )


@router.get("/analytics/evidence/{workspace_id}", response_model=EvidenceAnalyticsResponse)
async def evidence_analytics(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> EvidenceAnalyticsResponse:
    """Get evidence analytics for a workspace."""
    await _check_workspace_member(db, workspace_id, user.id)
    ev_repo = BaseRepository(db, Evidence)
    total = await ev_repo.count(workspace_id=workspace_id, is_deleted=False)
    by_status = {}
    for s in EvidenceStatus:
        cnt = await ev_repo.count(workspace_id=workspace_id, is_deleted=False, status=s)
        if cnt > 0:
            by_status[s.value] = cnt
    storage_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(Evidence.file_size), 0)).where(
            Evidence.workspace_id == workspace_id, Evidence.is_deleted == False
        )
    )
    total_storage = storage_result.scalar() or 0
    recent = await ev_repo.count(workspace_id=workspace_id, is_deleted=False)
    return EvidenceAnalyticsResponse(
        total=total, by_status=by_status,
        total_storage_bytes=total_storage, recent_uploads=recent,
    )


# ── Global Search ─────────────────────────────────────────────────────────────


@router.get("/search", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    _workspace_id: uuid.UUID | None = Query(None),
    entity_type: str | None = Query(None, description="Comma-separated: investigation,evidence,entity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> GlobalSearchResponse:
    """Global search across investigations, evidence, and entities."""
    ws_result = await db.execute(
        select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id)
    )
    ws_ids = [row[0] for row in ws_result.all()]
    if not ws_ids:
        return GlobalSearchResponse(results=[], total=0, query=q, skip=skip, limit=limit)

    query_filter = f"%{q}%"
    results: list[GlobalSearchResult] = []
    types_list = entity_type.split(",") if entity_type else ["investigation", "evidence", "entity"]

    if "investigation" in types_list:
        inv_stmt = select(Investigation).where(
            Investigation.workspace_id.in_(ws_ids),
            or_(Investigation.title.ilike(query_filter), Investigation.description.ilike(query_filter)),
        ).limit(limit)
        for inv in (await db.execute(inv_stmt)).scalars().all():
            results.append(GlobalSearchResult(
                id=str(inv.id), type="investigation",
                title=inv.title, description=inv.description,
                link=f"/investigations/{inv.id}", workspace_id=str(inv.workspace_id), score=1.0,
            ))

    if "evidence" in types_list:
        ev_stmt = select(Evidence).where(
            Evidence.workspace_id.in_(ws_ids), Evidence.is_deleted == False,
            or_(Evidence.title.ilike(query_filter), Evidence.description.ilike(query_filter),
                Evidence.evidence_number.ilike(query_filter), Evidence.original_filename.ilike(query_filter)),
        ).limit(limit)
        for ev in (await db.execute(ev_stmt)).scalars().all():
            results.append(GlobalSearchResult(
                id=str(ev.id), type="evidence",
                title=ev.title, description=ev.description,
                match_field=ev.evidence_number, link=f"/evidence/{ev.id}",
                workspace_id=str(ev.workspace_id), score=1.0,
            ))

    if "entity" in types_list:
        ent_stmt = select(Entity).where(Entity.label.ilike(query_filter)).limit(limit)
        for ent in (await db.execute(ent_stmt)).scalars().all():
            etype = ent.type.value if hasattr(ent.type, "value") else ent.type
            results.append(GlobalSearchResult(
                id=str(ent.id), type=f"entity_{etype}",
                title=ent.label, description=ent.description,
                link=f"/investigations/{ent.investigation_id}", score=1.0,
            ))

    return GlobalSearchResponse(
        results=results[:limit], total=len(results), query=q, skip=skip, limit=limit
    )
