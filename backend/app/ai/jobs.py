"""
Background job processing for AI operations.

Large AI requests that may take significant time execute asynchronously
via this module. Jobs are tracked in the AIJob table with lifecycle
states: queued → running → completed | failed | cancelled.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.ai.cache import ai_cache
from app.ai.providers.base import BaseProvider
from app.ai.service import AIService
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.ai_job import AIJob, AIJobStatus, AIJobType
from app.models.ai_suggestion import AISuggestion, SuggestionType
from app.repositories.base import BaseRepository

logger = get_logger(__name__)

# In-memory task registry for tracking running jobs
_running_jobs: dict[uuid.UUID, asyncio.Task[None]] = {}


async def process_job(job_id: uuid.UUID) -> None:
    """
    Process an AI job asynchronously.

    This function is designed to run as a background task. It updates
    the job status through its lifecycle and handles errors gracefully.

    Args:
        job_id: The UUID of the AIJob to process.
    """
    task = asyncio.create_task(_execute_job(job_id))
    _running_jobs[job_id] = task
    try:
        await task
    finally:
        _running_jobs.pop(job_id, None)


async def _execute_job(job_id: uuid.UUID) -> None:
    """Execute a single AI job with full lifecycle management."""
    async with AsyncSessionLocal() as db:
        try:
            repo = BaseRepository(db, AIJob)
            job = await repo.get(job_id)
            if not job:
                logger.error("Job not found for processing", job_id=str(job_id))
                return

            if job.status != AIJobStatus.QUEUED:
                logger.warning(
                    "Job not in queued state, skipping",
                    job_id=str(job_id),
                    status=job.status.value,
                )
                return

            job.mark_running()
            await db.flush()

            # Delegate to the appropriate handler
            svc = AIService(db)
            provider = svc._get_provider()
            prompt = await svc._load_prompt(job.job_type.value)

            result, usage_meta = await _run_job_operation(
                svc, provider, prompt, job, db
            )

            # Cache and finalize
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result
            ai_cache.set(
                str(job.evidence_ids or ""),
                prompt,
                provider.model,
                settings.AI_PROMPT_VERSION,
                result_dict,
            )

            job.mark_completed(
                result=result_dict,
                input_tokens=usage_meta.get("input_tokens", 0),
                output_tokens=usage_meta.get("output_tokens", 0),
                cost=usage_meta.get("cost", 0.0),
                latency_ms=usage_meta.get("latency_ms", 0),
            )
            await db.commit()

            logger.info(
                "Job completed",
                job_id=str(job_id),
                type=job.job_type.value,
                latency=usage_meta.get("latency_ms"),
            )

        except Exception as exc:
            logger.error("Job processing failed", job_id=str(job_id), error=str(exc))
            try:
                job = await repo.get(job_id)
                if job:
                    job.mark_failed(str(exc)[:1000])
                    await db.commit()
            except Exception:
                logger.exception("Failed to update job error status", job_id=str(job_id))


async def _run_job_operation(
    svc: AIService,
    provider: BaseProvider,
    prompt: str,
    job: AIJob,
    db: Any = None,  # Reuse existing session when available
) -> tuple[Any, dict[str, Any]]:
    """Route the job to the correct AI operation based on job type."""
    # Use the session from AIService when db is not explicitly passed
    session = db or svc.db

    result: Any = None

    if job.job_type == AIJobType.SUMMARIZE:
        evidence_text = await _load_evidence_batch(job.evidence_ids or [])
        result = await provider.summarize(evidence_text, prompt_template=prompt)
        return result, {}

    elif job.job_type == AIJobType.EXTRACT_ENTITIES:
        evidence_text = await _load_evidence_batch(job.evidence_ids or [])
        result = await provider.extract_entities(evidence_text, prompt_template=prompt)

        # Create pending suggestions reusing the existing session
        if result.entities and job.investigation_id:
            for entity_data in result.model_dump().get("entities", []):
                sug = AISuggestion(
                    job_id=job.id,
                    investigation_id=job.investigation_id,
                    workspace_id=job.workspace_id,
                    suggestion_type=SuggestionType.ENTITY,
                    data=entity_data,
                )
                session.add(sug)
            await session.commit()

        return result, {}

    elif job.job_type == AIJobType.SUGGEST_RELATIONSHIPS:
        evidence_text = await _load_evidence_batch(job.evidence_ids or [])
        entities_context = await _load_entities_context(job.investigation_id)
        result = await provider.suggest_relationships(
            entities_context, evidence_text, prompt_template=prompt
        )

        if result.relationships and job.investigation_id:
            for rel_data in result.model_dump().get("relationships", []):
                sug = AISuggestion(
                    job_id=job.id,
                    investigation_id=job.investigation_id,
                    workspace_id=job.workspace_id,
                    suggestion_type=SuggestionType.RELATIONSHIP,
                    data=rel_data,
                )
                session.add(sug)
            await session.commit()

        return result, {}

    elif job.job_type == AIJobType.GENERATE_TIMELINE:
        evidence_text = await _load_evidence_batch(job.evidence_ids or [])
        result = await provider.generate_timeline(evidence_text, prompt_template=prompt)

        if result.events and job.investigation_id:
            for event_data in result.model_dump().get("events", []):
                sug = AISuggestion(
                    job_id=job.id,
                    investigation_id=job.investigation_id,
                    workspace_id=job.workspace_id,
                    suggestion_type=SuggestionType.TIMELINE_EVENT,
                    data=event_data,
                )
                session.add(sug)
            await session.commit()

        return result, {}

    elif job.job_type == AIJobType.GENERATE_REPORT:
        inv_id = job.investigation_id or uuid.UUID(int=0)
        context = await svc._load_investigation_context(inv_id)
        result = await provider.generate_report(context, prompt_template=prompt)
        return result, {}

    else:
        raise ValueError(f"Unknown job type: {job.job_type}")


async def _load_evidence_batch(
    evidence_ids: list,
) -> str:
    """Load multiple evidence items and concatenate their text."""
    texts = []
    for eid in evidence_ids[:10]:
        try:
            ev_uuid = uuid.UUID(eid) if isinstance(eid, str) else eid
            # Use a system user for background jobs
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from app.models.evidence import Evidence
                ev_repo = BaseRepository(db, Evidence)
                ev = await ev_repo.get(ev_uuid)
                if ev and not ev.is_deleted:
                    parts = [
                        f"Title: {ev.title}",
                        f"Description: {ev.description or ''}",
                        f"Source: {ev.source or 'Unknown'}",
                        f"Category: {ev.category}",
                    ]
                    if ev.original_filename:
                        parts.append(f"Filename: {ev.original_filename}")
                    texts.append("\n".join(parts))
        except Exception:
            logger.warning("Failed to load evidence for job", evidence_id=str(eid))
    return "\n---\n".join(texts) if texts else "No evidence available."


async def _load_entities_context(
    investigation_id: uuid.UUID | None
) -> str:
    """Load entities for an investigation as context text."""
    from app.models.entity import Entity

    if not investigation_id:
        return "No entities available."

    async with AsyncSessionLocal() as db:
        entity_repo = BaseRepository(db, Entity)
        entities = await entity_repo.find_many(investigation_id=investigation_id)
        if not entities:
            return "No entities available."
        return "\n".join(
            f"{e.type.value if hasattr(e.type, 'value') else e.type}: {e.label}"
            for e in entities
        )


def cancel_job(job_id: uuid.UUID) -> bool:
    """
    Cancel a running background job.

    Args:
        job_id: The UUID of the job to cancel.

    Returns:
        True if the job was found and cancelled, False otherwise.
    """
    task = _running_jobs.get(job_id)
    if task and not task.done():
        task.cancel()
        return True
    return False
