"""
AI Intelligence Engine — core orchestration service.

Coordinates LLM providers, prompt management, caching, injection
detection, token tracking, and the human-review workflow.
Every AI action is auditable and requires human approval to modify
investigation data.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import ai_cache
from app.ai.injection_guard import validate_input
from app.ai.providers import (
    AnthropicProvider,
    AzureProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from app.ai.providers.base import BaseProvider
from app.ai.schemas import (
    AIJobResponse,
    AISuggestionResponse,
    AIUsageStats,
    PromptVersionResponse,
)
from app.ai.tokenizer import count_tokens, estimate_cost, truncate_to_token_limit
from app.core.circuit_breaker import ai_provider_breaker
from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai_job import AIJob, AIJobType
from app.models.ai_suggestion import AISuggestion, SuggestionStatus, SuggestionType
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.prompt_version import PromptVersion
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class AIService:
    """
    Core AI Intelligence Engine service.

    Orchestrates:
    - Provider selection and initialization
    - Prompt loading and versioning
    - Input validation and injection detection
    - Caching with SHA256 keying
    - Token counting and cost estimation
    - Audit logging via AIJob records
    - Human-review workflow via AISuggestion records
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._provider: BaseProvider | None = None
        self._prompts_cache: dict[str, str] = {}

    # ── Provider Management ───────────────────────────────────────────────────

    def _get_provider(self) -> BaseProvider:
        """Get or create the configured LLM provider."""
        if self._provider is not None:
            return self._provider

        provider_name = settings.AI_PROVIDER.lower()

        if provider_name == "openai":
            if not settings.OPENAI_API_KEY:
                pass
            self._provider = OpenAIProvider()
        elif provider_name == "ollama":
            self._provider = OllamaProvider()
        elif provider_name == "azure":
            self._provider = AzureProvider()
        elif provider_name == "anthropic":
            self._provider = AnthropicProvider()
        elif provider_name == "gemini":
            self._provider = GeminiProvider()
        else:
            raise ValueError(f"Unknown AI provider: {provider_name}")

        return self._provider

    @staticmethod
    def get_provider_info() -> dict[str, Any]:
        """Return information about all available providers."""
        from app.core.config import settings as s

        providers = [
            {
                "name": "openai",
                "display_name": "OpenAI",
                "available": bool(s.OPENAI_API_KEY),
                "model": s.OPENAI_MODEL,
                "supports_streaming": True,
            },
            {
                "name": "ollama",
                "display_name": "Ollama (Local)",
                "available": True,
                "model": s.OLLAMA_MODEL,
                "supports_streaming": True,
            },
            {
                "name": "azure",
                "display_name": "Azure OpenAI",
                "available": bool(s.AZURE_OPENAI_KEY),
                "model": s.AZURE_OPENAI_DEPLOYMENT or "gpt-4o",
                "supports_streaming": False,
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic Claude",
                "available": bool(s.ANTHROPIC_API_KEY),
                "model": s.ANTHROPIC_MODEL,
                "supports_streaming": True,
            },
            {
                "name": "gemini",
                "display_name": "Google Gemini",
                "available": bool(s.GEMINI_API_KEY),
                "model": s.GEMINI_MODEL,
                "supports_streaming": True,
            },
        ]
        return {"active": s.AI_PROVIDER, "providers": providers}

    # ── Prompt Management ─────────────────────────────────────────────────────

    async def _load_prompt(self, name: str) -> str:
        """Load a prompt template, preferring the active version from DB."""
        # Check in-memory cache first
        if name in self._prompts_cache:
            return self._prompts_cache[name]

        # Try to load from database
        try:
            repo = BaseRepository(self.db, PromptVersion)
            db_prompt = await repo.find_one(name=name, is_active=True)
            if db_prompt:
                self._prompts_cache[name] = db_prompt.content
                return db_prompt.content
        except Exception:
            pass

        # Fallback to file-based prompts
        file_prompt = await self._load_prompt_from_file(name)
        self._prompts_cache[name] = file_prompt
        return file_prompt

    async def _load_prompt_from_file(self, name: str) -> str:
        """Load a prompt template from the prompts directory."""
        import os

        prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
        filepath = os.path.join(prompt_dir, f"{name}.md")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt file not found: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            return f.read()

    async def list_prompts(self) -> list[PromptVersionResponse]:
        """List all active prompt versions."""
        repo = BaseRepository(self.db, PromptVersion)
        prompts = await repo.find_many(is_active=True, order_by="name")
        return [PromptVersionResponse.model_validate(p) for p in prompts]

    async def get_prompt_content(self, name: str) -> str:
        """Get the content of a prompt by name."""
        return await self._load_prompt(name)

    # ── Evidence Loading ──────────────────────────────────────────────────────

    async def _load_evidence_text(
        self, evidence_id: uuid.UUID, user_id: uuid.UUID, max_chars: int | None = None
    ) -> tuple[Evidence, str]:
        """Load evidence and extract its text content."""
        ev_repo = BaseRepository(self.db, Evidence)
        evidence = await ev_repo.get(evidence_id)
        if not evidence or evidence.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found",
            )

        # Verify workspace membership via the evidence's workspace
        from app.models.workspace_member import WorkspaceMember
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(
            workspace_id=evidence.workspace_id, user_id=user_id
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace"
            )

        # Build text content from evidence fields
        parts = [
            f"Title: {evidence.title}",
            f"Evidence Number: {evidence.evidence_number}",
            f"Category: {evidence.category}",
            f"Source: {evidence.source or 'Unknown'}",
        ]
        if evidence.description:
            parts.append(f"Description: {evidence.description}")

        if evidence.original_filename:
            parts.append(f"Filename: {evidence.original_filename}")

        if evidence.sha256_hash:
            parts.append(f"SHA256: {evidence.sha256_hash}")

        text = "\n".join(parts)
        max_chars = max_chars or settings.AI_SUMMARIZE_MAX_CHARS
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[TRUNCATED]"
        return evidence, text

    async def _load_investigation_context(self, investigation_id: uuid.UUID) -> str:
        """Build a comprehensive context string for an investigation."""
        inv_repo = BaseRepository(self.db, Investigation)
        investigation = await inv_repo.get(investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found",
            )

        parts = [
            f"Investigation: {investigation.title}",
            f"Status: {investigation.status.value if hasattr(investigation.status, 'value') else investigation.status}",
            f"Priority: {investigation.priority.value if hasattr(investigation.priority, 'value') else investigation.priority}",
        ]
        if investigation.description:
            parts.append(f"Description: {investigation.description}")

        # Load entities
        from app.models.entity import Entity
        entity_repo = BaseRepository(self.db, Entity)
        entities = await entity_repo.find_many(investigation_id=investigation_id)
        if entities:
            parts.append("\n## Entities")
            for e in entities:
                etype = e.type.value if hasattr(e.type, "value") else e.type
                parts.append(f"- {etype}: {e.label}")
                if e.description:
                    parts.append(f"  - {e.description}")

        # Load relationships
        from app.models.relationship import Relationship
        rel_repo = BaseRepository(self.db, Relationship)
        rels = await rel_repo.find_many(investigation_id=investigation_id)
        if rels:
            parts.append("\n## Relationships")
            for r in rels:
                rtype = r.relationship_type.value if hasattr(r.relationship_type, "value") else r.relationship_type
                parts.append(f"- {r.source_entity_id} --[{rtype}]--> {r.target_entity_id}")
                if r.notes:
                    parts.append(f"  - {r.notes}")

        # Load timeline events
        from app.models.timeline_event import TimelineEvent
        timeline_repo = BaseRepository(self.db, TimelineEvent)
        events = await timeline_repo.find_many(
            investigation_id=investigation_id, order_by="event_timestamp"
        )
        if events:
            parts.append("\n## Timeline")
            for ev in events:
                ts = ev.event_timestamp.isoformat() if ev.event_timestamp else "?"
                parts.append(f"- [{ts}] {ev.title}: {ev.description or ''}")

        return "\n".join(parts)

    # ── Workspace / Investigation Access Helpers ──────────────────────────────

    async def _check_workspace_access(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Verify the user is a member of the workspace."""
        from app.models.workspace_member import WorkspaceMember
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )

    async def _get_investigation_workspace(
        self, investigation_id: uuid.UUID
    ) -> uuid.UUID:
        """Get the workspace_id for an investigation."""
        inv_repo = BaseRepository(self.db, Investigation)
        investigation = await inv_repo.get(investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found",
            )
        return investigation.workspace_id

    async def _get_evidence_workspace(self, evidence_id: uuid.UUID) -> uuid.UUID:
        """Get the workspace_id from evidence."""
        ev_repo = BaseRepository(self.db, Evidence)
        evidence = await ev_repo.get(evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found",
            )
        return evidence.workspace_id

    # ── Core AI Operations ────────────────────────────────────────────────────

    async def _call_with_timeout(
        self, provider: BaseProvider, method: str, *,
        timeout: int | None = None, **kwargs: Any,
    ) -> Any:
        """Call an AI provider method with timeout and circuit breaker protection."""
        timeout_s = timeout or settings.AI_TIMEOUT_SECONDS
        call_fn = getattr(provider, method)
        async with ai_provider_breaker:
            try:
                result = await asyncio.wait_for(
                    call_fn(**kwargs),
                    timeout=timeout_s,
                )
                return result
            except TimeoutError as exc:
                logger.error(
                    "AI provider timed out",
                    provider=provider.name,
                    method=method,
                    timeout=timeout_s,
                )
                raise TimeoutError(
                    f"AI provider '{provider.name}' timed out after {timeout_s}s"
                ) from exc

    async def summarize(
        self,
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
        max_length: int | None = None,
    ) -> AIJobResponse:
        """Summarize a single evidence item. Returns the AI job record."""
        evidence, text = await self._load_evidence_text(evidence_id, user_id)
        provider = self._get_provider()
        prompt = await self._load_prompt("summarize")

        # Check provider availability
        if not settings.OPENAI_API_KEY and settings.AI_PROVIDER.lower() == "openai":
            # Return a failed job immediately instead of 500
            job = await self._create_job(
                user_id=user_id,
                workspace_id=evidence.workspace_id,
                job_type=AIJobType.SUMMARIZE,
                evidence_ids=[str(evidence_id)],
            )
            job.mark_failed("AI provider not configured — no API key set")
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        # Validate input
        validate_input(text, max_length=settings.AI_SUMMARIZE_MAX_CHARS)

        # Create job record
        job = await self._create_job(
            user_id=user_id,
            workspace_id=evidence.workspace_id,
            job_type=AIJobType.SUMMARIZE,
            evidence_ids=[str(evidence_id)],
        )

        # Check cache
        cached, cached_result = ai_cache.get(text, prompt, provider.model, settings.AI_PROMPT_VERSION)
        if cached and cached_result is not None:
            job.mark_completed(
                result=cached_result,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0,
                cached=True,
            )
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        # Truncate if needed
        token_count = count_tokens(text, provider.model)
        if token_count > settings.AI_MAX_INPUT_TOKENS:
            text = truncate_to_token_limit(text, settings.AI_MAX_INPUT_TOKENS, provider.model)

        try:
            result = await self._call_with_timeout(
                provider, "summarize", evidence_text=text, prompt_template=prompt, max_length=max_length,
            )
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        # Cache and persist
        result_dict = result.model_dump()
        ai_cache.set(text, prompt, provider.model, settings.AI_PROMPT_VERSION, result_dict)

        input_tok = count_tokens(text, provider.model)
        output_tok = count_tokens(str(result_dict), provider.model)
        cost = estimate_cost(input_tok, output_tok, provider.model)

        job.mark_completed(
            result=result_dict,
            input_tokens=input_tok,
            output_tokens=output_tok,
            cost=cost,
            latency_ms=0,
        )
        await self.db.commit()
        await self.db.refresh(job)
        return AIJobResponse.model_validate(job)

    async def extract_entities(
        self,
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: uuid.UUID | None = None,
    ) -> AIJobResponse:
        """Extract entities from evidence. Returns the AI job with suggestions created."""
        evidence, text = await self._load_evidence_text(evidence_id, user_id)
        provider = self._get_provider()
        prompt = await self._load_prompt("entities")

        # Check provider availability
        if not settings.OPENAI_API_KEY and settings.AI_PROVIDER.lower() == "openai":
            job = await self._create_job(
                user_id=user_id,
                workspace_id=evidence.workspace_id,
                investigation_id=investigation_id,
                job_type=AIJobType.EXTRACT_ENTITIES,
                evidence_ids=[str(evidence_id)],
            )
            job.mark_failed("AI provider not configured — no API key set")
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        validate_input(text, max_length=settings.AI_SUMMARIZE_MAX_CHARS)

        job = await self._create_job(
            user_id=user_id,
            workspace_id=evidence.workspace_id,
            investigation_id=investigation_id,
            job_type=AIJobType.EXTRACT_ENTITIES,
            evidence_ids=[str(evidence_id)],
        )

        cached, cached_result = ai_cache.get(text, prompt, provider.model, settings.AI_PROMPT_VERSION)
        if cached and cached_result is not None:
            job.mark_completed(
                result=cached_result,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=0,
                cached=True,
            )
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        token_count = count_tokens(text, provider.model)
        if token_count > settings.AI_MAX_INPUT_TOKENS:
            text = truncate_to_token_limit(text, settings.AI_MAX_INPUT_TOKENS, provider.model)

        try:
            result = await self._call_with_timeout(
                provider, "extract_entities", evidence_text=text, prompt_template=prompt,
            )
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        result_dict = result.model_dump()
        ai_cache.set(text, prompt, provider.model, settings.AI_PROMPT_VERSION, result_dict)

        input_tok = count_tokens(text, provider.model)
        output_tok = count_tokens(str(result_dict), provider.model)
        cost = estimate_cost(input_tok, output_tok, provider.model)

        job.mark_completed(
            result=result_dict,
            input_tokens=input_tok,
            output_tokens=output_tok,
            cost=cost,
            latency_ms=0,
        )

        # Create pending suggestions only if tied to an investigation
        if result.entities and investigation_id:
            await self._create_entity_suggestions(
                job.id, investigation_id, evidence.workspace_id, result_dict.get("entities", [])
            )

        await self.db.commit()
        await self.db.refresh(job)
        return AIJobResponse.model_validate(job)

    async def suggest_relationships(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        evidence_ids: list[uuid.UUID] | None = None,
    ) -> AIJobResponse:
        """Suggest relationships between entities in an investigation."""
        workspace_id = await self._get_investigation_workspace(investigation_id)
        await self._check_workspace_access(workspace_id, user_id)
        provider = self._get_provider()
        prompt = await self._load_prompt("relationships")

        # Gather evidence text
        evidence_text = ""
        if evidence_ids:
            for eid in evidence_ids[:10]:  # Limit to 10 evidence items
                _, text = await self._load_evidence_text(eid, user_id, max_chars=5000)
                evidence_text += f"\n--- Evidence ---\n{text}\n"

        # Get entities context
        from app.models.entity import Entity
        entity_repo = BaseRepository(self.db, Entity)
        entities = await entity_repo.find_many(investigation_id=investigation_id)
        entities_context = "\n".join(
            f"{e.type.value if hasattr(e.type, 'value') else e.type}: {e.label}"
            for e in entities
        ) or "No entities yet."

        job = await self._create_job(
            user_id=user_id,
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            job_type=AIJobType.SUGGEST_RELATIONSHIPS,
            evidence_ids=[str(e) for e in evidence_ids] if evidence_ids else None,
        )

        combined_text = f"Entities:\n{entities_context}\n\nEvidence:\n{evidence_text}"

        cached, cached_result = ai_cache.get(
            combined_text, prompt, provider.model, settings.AI_PROMPT_VERSION
        )
        if cached and cached_result is not None:
            job.mark_completed(result=cached_result, input_tokens=0, output_tokens=0, cost=0.0, latency_ms=0, cached=True)
            await self.db.commit()
            await self.db.refresh(job)
            if cached_result.get("relationships"):
                await self._create_relationship_suggestions(
                    job.id, investigation_id, workspace_id, cached_result["relationships"]
                )
            return AIJobResponse.model_validate(job)

        try:
            result = await self._call_with_timeout(
                provider, "suggest_relationships",
                entities_context=entities_context, evidence_text=evidence_text, prompt_template=prompt,
            )
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        result_dict = result.model_dump()
        ai_cache.set(combined_text, prompt, provider.model, settings.AI_PROMPT_VERSION, result_dict)

        input_tok = count_tokens(combined_text, provider.model)
        output_tok = count_tokens(str(result_dict), provider.model)
        cost = estimate_cost(input_tok, output_tok, provider.model)

        job.mark_completed(result=result_dict, input_tokens=input_tok, output_tokens=output_tok, cost=cost, latency_ms=0)

        if result.relationships:
            await self._create_relationship_suggestions(
                job.id, investigation_id, workspace_id, result_dict.get("relationships", [])
            )

        await self.db.commit()
        await self.db.refresh(job)
        return AIJobResponse.model_validate(job)

    async def generate_timeline(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        evidence_ids: list[uuid.UUID] | None = None,
    ) -> AIJobResponse:
        """Generate timeline events from investigation evidence."""
        workspace_id = await self._get_investigation_workspace(investigation_id)
        await self._check_workspace_access(workspace_id, user_id)
        provider = self._get_provider()
        prompt = await self._load_prompt("timeline")

        # Gather evidence text
        evidence_text_parts = []
        if evidence_ids:
            for eid in evidence_ids[:10]:
                _, text = await self._load_evidence_text(eid, user_id, max_chars=5000)
                evidence_text_parts.append(text)
        else:
            # Load all evidence for the workspace
            ev_repo = BaseRepository(self.db, Evidence)
            all_evidence = await ev_repo.find_many(workspace_id=workspace_id, is_deleted=False, limit=20)
            for ev in all_evidence:
                _, text = await self._load_evidence_text(ev.id, user_id, max_chars=3000)
                evidence_text_parts.append(text)

        combined_text = "\n---\n".join(evidence_text_parts) or "No evidence available."

        job = await self._create_job(
            user_id=user_id,
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            job_type=AIJobType.GENERATE_TIMELINE,
        )

        cached, cached_result = ai_cache.get(combined_text, prompt, provider.model, settings.AI_PROMPT_VERSION)
        if cached and cached_result is not None:
            job.mark_completed(result=cached_result, input_tokens=0, output_tokens=0, cost=0.0, latency_ms=0, cached=True)
            await self.db.commit()
            await self.db.refresh(job)
            if cached_result.get("events"):
                await self._create_timeline_suggestions(
                    job.id, investigation_id, workspace_id, cached_result["events"]
                )
            return AIJobResponse.model_validate(job)

        try:
            result = await self._call_with_timeout(
                provider, "generate_timeline", evidence_text=combined_text, prompt_template=prompt,
            )
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        result_dict = result.model_dump()
        ai_cache.set(combined_text, prompt, provider.model, settings.AI_PROMPT_VERSION, result_dict)

        input_tok = count_tokens(combined_text, provider.model)
        output_tok = count_tokens(str(result_dict), provider.model)
        cost = estimate_cost(input_tok, output_tok, provider.model)

        job.mark_completed(result=result_dict, input_tokens=input_tok, output_tokens=output_tok, cost=cost, latency_ms=0)

        if result.events:
            await self._create_timeline_suggestions(
                job.id, investigation_id, workspace_id, result_dict.get("events", [])
            )

        await self.db.commit()
        await self.db.refresh(job)
        return AIJobResponse.model_validate(job)

    async def generate_report(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIJobResponse:
        """Generate a complete investigation report."""
        workspace_id = await self._get_investigation_workspace(investigation_id)
        await self._check_workspace_access(workspace_id, user_id)
        provider = self._get_provider()
        prompt = await self._load_prompt("report")

        context = await self._load_investigation_context(investigation_id)

        job = await self._create_job(
            user_id=user_id,
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            job_type=AIJobType.GENERATE_REPORT,
        )

        cached, cached_result = ai_cache.get(context, prompt, provider.model, settings.AI_PROMPT_VERSION)
        if cached and cached_result is not None:
            job.mark_completed(result=cached_result, input_tokens=0, output_tokens=0, cost=0.0, latency_ms=0, cached=True)
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        try:
            result = await self._call_with_timeout(
                provider, "generate_report", investigation_context=context, prompt_template=prompt,
            )
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.db.commit()
            await self.db.refresh(job)
            return AIJobResponse.model_validate(job)

        result_dict = result.model_dump()
        ai_cache.set(context, prompt, provider.model, settings.AI_PROMPT_VERSION, result_dict)

        input_tok = count_tokens(context, provider.model)
        output_tok = count_tokens(str(result_dict), provider.model)
        cost = estimate_cost(input_tok, output_tok, provider.model)

        job.mark_completed(result=result_dict, input_tokens=input_tok, output_tokens=output_tok, cost=cost, latency_ms=0)
        await self.db.commit()
        await self.db.refresh(job)
        return AIJobResponse.model_validate(job)

    # ── Job Management ────────────────────────────────────────────────────────

    async def _create_job(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        job_type: AIJobType,
        investigation_id: uuid.UUID | None = None,
        evidence_ids: list[str] | None = None,
    ) -> AIJob:
        """Create a new AI job record."""
        provider = self._get_provider()
        job = AIJob(
            user_id=user_id,
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            job_type=job_type,
            provider=provider.name,
            model=provider.model,
            evidence_ids=evidence_ids,
        )
        job.mark_running()
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> AIJobResponse:
        """Get an AI job by ID with access check."""
        repo = BaseRepository(self.db, AIJob)
        job = await repo.get(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await self._check_workspace_access(job.workspace_id, user_id)
        return AIJobResponse.model_validate(job)

    async def list_jobs(
        self, workspace_id: uuid.UUID | None, user_id: uuid.UUID, limit: int = 50
    ) -> list[AIJobResponse]:
        """List recent AI jobs for a workspace (or all accessible workspaces)."""
        repo = BaseRepository(self.db, AIJob)
        if workspace_id:
            await self._check_workspace_access(workspace_id, user_id)
            jobs = await repo.find_many(
                workspace_id=workspace_id, order_by="created_at", descending=True, limit=limit
            )
        else:
            # Get all workspaces the user belongs to
            from app.models.workspace_member import WorkspaceMember
            ws_repo = BaseRepository(self.db, WorkspaceMember)
            memberships = await ws_repo.find_many(user_id=user_id)
            ws_ids = [m.workspace_id for m in memberships]
            if not ws_ids:
                return []
            from sqlalchemy import select as sa_select
            stmt = sa_select(AIJob).where(AIJob.workspace_id.in_(ws_ids)).order_by(AIJob.created_at.desc()).limit(limit)
            result = await self.db.execute(stmt)
            jobs = list(result.scalars().all())
        return [AIJobResponse.model_validate(j) for j in jobs]

    async def get_usage_stats(
        self, workspace_id: uuid.UUID | None, user_id: uuid.UUID
    ) -> AIUsageStats:
        """Get aggregate AI usage statistics."""
        query = select(AIJob)

        if workspace_id:
            await self._check_workspace_access(workspace_id, user_id)
            query = query.where(AIJob.workspace_id == workspace_id)
        else:
            from app.models.workspace_member import WorkspaceMember
            subq = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
            query = query.where(AIJob.workspace_id.in_(subq))

        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        if not jobs:
            return AIUsageStats()

        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_latency = 0
        cache_hits = 0
        jobs_today = 0
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        for job in jobs:
            jt = job.job_type.value if hasattr(job.job_type, "value") else str(job.job_type)
            js = job.status.value if hasattr(job.status, "value") else str(job.status)
            by_type[jt] = by_type.get(jt, 0) + 1
            by_status[js] = by_status.get(js, 0) + 1
            total_input += job.input_tokens or 0
            total_output += job.output_tokens or 0
            total_cost += job.cost or 0.0
            total_latency += job.latency_ms or 0
            if job.cached:
                cache_hits += 1
            if job.created_at and job.created_at >= today_start:
                jobs_today += 1

        # Count pending suggestions
        sug_repo = BaseRepository(self.db, AISuggestion)
        pending_count = 0
        if workspace_id:
            pending_count = await sug_repo.count(
                workspace_id=workspace_id, status=SuggestionStatus.PENDING
            )

        return AIUsageStats(
            total_jobs=len(jobs),
            by_type=by_type,
            by_status=by_status,
            total_tokens_input=total_input,
            total_tokens_output=total_output,
            total_cost=round(total_cost, 4),
            average_latency_ms=round(total_latency / len(jobs), 1) if jobs else 0.0,
            cache_hits=cache_hits,
            jobs_today=jobs_today,
            pending_suggestions=pending_count,
        )

    # ── Human Review Workflow ─────────────────────────────────────────────────

    async def _create_entity_suggestions(
        self,
        job_id: uuid.UUID,
        investigation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        entities: list[dict],
    ) -> list[AISuggestion]:
        """Create pending entity suggestions from AI extraction results."""
        suggestions = []
        for entity_data in entities:
            suggestion = AISuggestion(
                job_id=job_id,
                investigation_id=investigation_id,
                workspace_id=workspace_id,
                suggestion_type=SuggestionType.ENTITY,
                data=entity_data,
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)
        if suggestions:
            await self.db.flush()
        return suggestions

    async def _create_relationship_suggestions(
        self,
        job_id: uuid.UUID,
        investigation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        relationships: list[dict],
    ) -> list[AISuggestion]:
        """Create pending relationship suggestions."""
        suggestions = []
        for rel_data in relationships:
            suggestion = AISuggestion(
                job_id=job_id,
                investigation_id=investigation_id,
                workspace_id=workspace_id,
                suggestion_type=SuggestionType.RELATIONSHIP,
                data=rel_data,
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)
        if suggestions:
            await self.db.flush()
        return suggestions

    async def _create_timeline_suggestions(
        self,
        job_id: uuid.UUID,
        investigation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        events: list[dict],
    ) -> list[AISuggestion]:
        """Create pending timeline event suggestions."""
        suggestions = []
        for event_data in events:
            suggestion = AISuggestion(
                job_id=job_id,
                investigation_id=investigation_id,
                workspace_id=workspace_id,
                suggestion_type=SuggestionType.TIMELINE_EVENT,
                data=event_data,
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)
        if suggestions:
            await self.db.flush()
        return suggestions

    async def list_suggestions(
        self,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        status: SuggestionStatus | None = None,
    ) -> list[AISuggestionResponse]:
        """List suggestions for an investigation."""
        workspace_id = await self._get_investigation_workspace(investigation_id)
        await self._check_workspace_access(workspace_id, user_id)

        repo = BaseRepository(self.db, AISuggestion)
        filters: dict[str, Any] = {"investigation_id": investigation_id}
        if status:
            filters["status"] = status

        suggestions = await repo.find_many(
            **filters, order_by="created_at", descending=True
        )
        return [AISuggestionResponse.model_validate(s) for s in suggestions]

    async def approve_suggestion(
        self,
        suggestion_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str | None = None,
    ) -> AISuggestionResponse:
        """Approve a suggestion and persist the data to the investigation."""
        repo = BaseRepository(self.db, AISuggestion)
        suggestion = await repo.get(suggestion_id)
        if not suggestion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

        await self._check_workspace_access(suggestion.workspace_id, user_id)

        if suggestion.status != SuggestionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Suggestion is already {suggestion.status.value}",
            )

        # Persist the suggestion data to the investigation
        await self._persist_suggestion(suggestion, user_id)

        suggestion.approve(reviewer_id=user_id, notes=notes)
        await self.db.commit()
        await self.db.refresh(suggestion)

        logger.info(
            "Suggestion approved",
            suggestion_id=str(suggestion.id),
            type=suggestion.suggestion_type.value,
            reviewer=str(user_id),
        )

        return AISuggestionResponse.model_validate(suggestion)

    async def reject_suggestion(
        self,
        suggestion_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str | None = None,
    ) -> AISuggestionResponse:
        """Reject a suggestion without persisting data."""
        repo = BaseRepository(self.db, AISuggestion)
        suggestion = await repo.get(suggestion_id)
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )

        await self._check_workspace_access(suggestion.workspace_id, user_id)

        if suggestion.status != SuggestionStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Suggestion is already {suggestion.status.value}",
            )

        suggestion.reject(reviewer_id=user_id, notes=notes)
        await self.db.commit()
        await self.db.refresh(suggestion)

        logger.info(
            "Suggestion rejected",
            suggestion_id=str(suggestion.id),
            type=suggestion.suggestion_type.value,
            reviewer=str(user_id),
        )

        return AISuggestionResponse.model_validate(suggestion)

    async def bulk_review(
        self,
        suggestion_ids: list[uuid.UUID],
        action: str,
        user_id: uuid.UUID,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Approve or reject multiple suggestions at once."""
        approved_count = 0
        rejected_count = 0
        errors: list[dict[str, str]] = []

        for sid in suggestion_ids:
            try:
                if action == "approve":
                    await self.approve_suggestion(sid, user_id, notes=notes)
                    approved_count += 1
                else:
                    await self.reject_suggestion(sid, user_id, notes=notes)
                    rejected_count += 1
            except (HTTPException, ValueError) as exc:
                errors.append({"suggestion_id": str(sid), "error": str(exc)})

        return {"approved": approved_count, "rejected": rejected_count, "errors": errors}

    async def _persist_suggestion(
        self, suggestion: AISuggestion, user_id: uuid.UUID
    ) -> None:
        """Persist an approved suggestion to the investigation database."""
        from app.models.entity import Entity
        from app.models.relationship import Relationship
        from app.models.timeline_event import TimelineEvent

        data = suggestion.data

        try:
            if suggestion.suggestion_type == SuggestionType.ENTITY:
                entity = Entity(
                    investigation_id=suggestion.investigation_id,
                    type=data.get("type", "custom"),
                    label=data.get("label", "Unknown"),
                    description=data.get("context"),
                    created_by=user_id,
                )
                self.db.add(entity)

            elif suggestion.suggestion_type == SuggestionType.RELATIONSHIP:
                # Look up entities by label
                entity_repo = BaseRepository(self.db, Entity)
                src_entities = await entity_repo.find_many(
                    investigation_id=suggestion.investigation_id,
                    label=data.get("source_entity_label", ""),
                )
                tgt_entities = await entity_repo.find_many(
                    investigation_id=suggestion.investigation_id,
                    label=data.get("target_entity_label", ""),
                )

                if src_entities and tgt_entities:
                    rel = Relationship(
                        investigation_id=suggestion.investigation_id,
                        source_entity_id=src_entities[0].id,
                        target_entity_id=tgt_entities[0].id,
                        relationship_type=data.get("relationship_type", "custom"),
                        confidence=data.get("confidence"),
                        notes=data.get("reasoning"),
                    )
                    self.db.add(rel)

            elif suggestion.suggestion_type == SuggestionType.TIMELINE_EVENT:
                from datetime import datetime

                event = TimelineEvent(
                    investigation_id=suggestion.investigation_id,
                    event_timestamp=datetime.now(UTC),
                    title=data.get("title", "AI-generated event"),
                    description=data.get("description"),
                    created_by=user_id,
                )
                self.db.add(event)

        except Exception as exc:
            logger.error(
                "Failed to persist suggestion",
                suggestion_id=str(suggestion.id),
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist suggestion: {exc}",
            ) from exc

    async def health_check(self) -> dict[str, Any]:
        """Check AI engine health — provider connectivity and cache status."""
        provider = self._get_provider()
        provider_healthy = await provider.health_check()
        return {
            "provider": provider.name,
            "model": provider.model,
            "provider_healthy": provider_healthy,
            "cache": ai_cache.stats,
            "active_prompt_version": settings.AI_PROMPT_VERSION,
        }
