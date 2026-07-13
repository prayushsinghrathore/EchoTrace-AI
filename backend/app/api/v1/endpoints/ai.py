"""
AI Intelligence Engine API endpoints.

All AI operations are gated by workspace RBAC, input validation,
and the human-review workflow. AI NEVER directly modifies investigation
data without explicit approval.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    AIBulkReviewRequest,
    AIExtractEntitiesRequest,
    AIJobResponse,
    AIRelationshipsRequest,
    AIReportRequest,
    AIReviewAction,
    AISuggestionResponse,
    AISummarizeRequest,
    AITimelineRequest,
    AIUsageStats,
    PromptVersionResponse,
)
from app.ai.service import AIService
from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.models.ai_suggestion import SuggestionStatus
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(tags=["ai"])


# ── Provider Info ─────────────────────────────────────────────────────────────


@router.get("/providers", response_model=dict)
async def list_providers(
    _user: User = Depends(get_current_user),
) -> dict:
    """List available AI providers and their configuration status."""
    return AIService.get_provider_info()


# ── Prompt Management ─────────────────────────────────────────────────────────


@router.get("/prompts", response_model=list[PromptVersionResponse])
async def list_prompts(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> list[PromptVersionResponse]:
    """List all active prompt versions."""
    svc = AIService(db)
    return await svc.list_prompts()


@router.get("/prompts/{name}/content")
async def get_prompt_content(
    name: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Get the raw content of a prompt by name."""
    svc = AIService(db)
    try:
        content = await svc.get_prompt_content(name)
        return {"name": name, "content": content}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── AI Operations ─────────────────────────────────────────────────────────────


@router.post("/summarize", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def summarize_evidence(
    body: AISummarizeRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """
    Summarize a single evidence item.

    Returns an AIJob immediately. The job processes synchronously for
    small evidence items; large items are chunked automatically.
    """
    svc = AIService(db)
    return await svc.summarize(
        evidence_id=body.evidence_id,
        user_id=user.id,
        max_length=body.max_length,
    )


@router.post("/entities", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_entities(
    body: AIExtractEntitiesRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """
    Extract entities from evidence.

    When an investigation_id is provided, extracted entities are stored
    as pending suggestions awaiting human review.
    """
    svc = AIService(db)
    return await svc.extract_entities(
        evidence_id=body.evidence_id,
        user_id=user.id,
        investigation_id=body.investigation_id,
    )


@router.post("/relationships", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def suggest_relationships(
    body: AIRelationshipsRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """
    Suggest relationships between entities in an investigation.

    Suggestions are stored as pending and require investigator approval.
    """
    svc = AIService(db)
    return await svc.suggest_relationships(
        investigation_id=body.investigation_id,
        user_id=user.id,
        evidence_ids=body.evidence_ids,
    )


@router.post("/timeline", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_timeline(
    body: AITimelineRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """
    Generate a timeline of events from investigation evidence.

    Timeline events are stored as pending suggestions awaiting review.
    """
    svc = AIService(db)
    return await svc.generate_timeline(
        investigation_id=body.investigation_id,
        user_id=user.id,
        evidence_ids=body.evidence_ids,
    )


@router.post("/report", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    body: AIReportRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """
    Generate a complete investigation report.

    Returns the report as a structured JSON job result.
    """
    svc = AIService(db)
    return await svc.generate_report(
        investigation_id=body.investigation_id,
        user_id=user.id,
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────


@router.post("/pipeline", status_code=status.HTTP_202_ACCEPTED)
async def run_ai_pipeline(
    evidence_id: uuid.UUID = Query(...),
    investigation_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Run the full AI analysis pipeline on an evidence item.

    Queues summarize + extract_entities as background jobs.
    Returns the job IDs so the frontend can poll for completion.
    """
    svc = AIService(db)

    # Queue summarize job
    summarize_job = await svc.summarize(
        evidence_id=evidence_id,
        user_id=user.id,
    )

    # Queue entity extraction (creates pending suggestions if investigation_id)
    entities_job = await svc.extract_entities(
        evidence_id=evidence_id,
        user_id=user.id,
        investigation_id=investigation_id,
    )

    return {
        "pipeline": "started",
        "jobs": [
            {"job_type": "summarize", "job_id": str(summarize_job.id), "status": summarize_job.status},
            {"job_type": "extract_entities", "job_id": str(entities_job.id), "status": entities_job.status},
        ],
        "evidence_id": str(evidence_id),
        "investigation_id": str(investigation_id) if investigation_id else None,
    }


# ── Job Management ────────────────────────────────────────────────────────────


@router.get("/jobs/{job_id}", response_model=AIJobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIJobResponse:
    """Get the status and result of an AI job."""
    svc = AIService(db)
    return await svc.get_job(job_id, user.id)


@router.get("/jobs", response_model=list[AIJobResponse])
async def list_jobs(
    workspace_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[AIJobResponse]:
    """List recent AI jobs for a workspace."""
    svc = AIService(db)
    return await svc.list_jobs(workspace_id, user.id, limit=limit)


# ── Usage Statistics ──────────────────────────────────────────────────────────


@router.get("/usage", response_model=AIUsageStats)
async def get_usage_stats(
    workspace_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AIUsageStats:
    """Get aggregate AI usage statistics."""
    svc = AIService(db)
    return await svc.get_usage_stats(workspace_id, user.id)


# ─── Health ────────────────────────────────────────────────────────────────────


@router.get("/health")
async def ai_health(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Check AI engine health — provider connectivity and cache status."""
    svc = AIService(db)
    return await svc.health_check()


# ── Human Review Workflow ─────────────────────────────────────────────────────


@router.get("/suggestions", response_model=list[AISuggestionResponse])
async def list_suggestions(
    investigation_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[AISuggestionResponse]:
    """List AI suggestions for an investigation, optionally filtered by status."""
    svc = AIService(db)
    status_value = None
    if status_filter:
        try:
            status_value = SuggestionStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            ) from None
    return await svc.list_suggestions(investigation_id, user.id, status=status_value)


@router.post("/review/{suggestion_id}/approve", response_model=AISuggestionResponse)
async def approve_suggestion(
    suggestion_id: uuid.UUID,
    body: AIReviewAction = AIReviewAction(notes=None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AISuggestionResponse:
    """
    Approve an AI suggestion and persist it to the investigation.

    This is the ONLY way AI-generated data enters the investigation.
    """
    svc = AIService(db)
    return await svc.approve_suggestion(suggestion_id, user.id, notes=body.notes)


@router.post("/review/{suggestion_id}/reject", response_model=AISuggestionResponse)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    body: AIReviewAction = AIReviewAction(notes=None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> AISuggestionResponse:
    """
    Reject an AI suggestion. The suggestion will be marked as rejected
    and will NOT be persisted to the investigation.
    """
    svc = AIService(db)
    return await svc.reject_suggestion(suggestion_id, user.id, notes=body.notes)


@router.post("/review/bulk")
async def bulk_review(
    body: AIBulkReviewRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Approve or reject multiple suggestions at once.

    Accepts a list of suggestion IDs and an action (approve|reject).
    """
    svc = AIService(db)
    return await svc.bulk_review(body.suggestion_ids, body.action, user.id, notes=body.notes)
