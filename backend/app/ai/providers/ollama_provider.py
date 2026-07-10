"""
Ollama LLM provider.

Connects to a local Ollama instance for self-hosted LLM inference.
Uses the Ollama API directly via HTTP.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.ai.providers.base import BaseProvider
from app.ai.schemas import (
    ExtractedEntitiesResult,
    GeneratedTimelineResult,
    ReportResult,
    SuggestedRelationshipsResult,
    SummaryResult,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaProvider(BaseProvider):
    """LLM provider using a local Ollama instance."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.OLLAMA_MODEL
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        return self._client

    async def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[Any],
        max_tokens: int | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        client = await self._get_client()
        start = time.time()

        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "num_predict": max_tokens or settings.AI_MAX_TOKENS,
                "temperature": 0.1,
            },
            "stream": False,
            "format": "json",
        }

        try:
            response = await client.post("/api/chat", json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise TimeoutError(f"Ollama request timed out after {settings.AI_TIMEOUT_SECONDS}s") from None
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama API error", status=exc.response.status_code)
            raise RuntimeError(f"Ollama API error: {exc.response.status_code}") from exc

        elapsed = int((time.time() - start) * 1000)

        content = data.get("message", {}).get("content", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        # Parse JSON from content (Ollama may return markdown-wrapped JSON)
        try:
            # Try direct parse first
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    raise ValueError(f"Ollama returned invalid JSON: {content[:300]}") from None
            else:
                raise ValueError(f"Ollama returned non-JSON content: {content[:300]}") from None

        try:
            result = response_schema.model_validate(parsed)
        except ValueError as exc:
            logger.error("Schema validation failed", error=str(exc), content=str(parsed)[:200])
            raise ValueError(f"LLM output failed schema validation: {exc}") from exc

        cost = 0.0  # Ollama is free/local

        usage_meta = {
            "input_tokens": prompt_eval_count,
            "output_tokens": eval_count,
            "cost": cost,
            "latency_ms": elapsed,
        }

        return result, usage_meta

    async def summarize(
        self,
        evidence_text: str,
        max_length: int | None = None,
        prompt_template: str | None = None,
    ) -> SummaryResult:
        system_prompt = prompt_template or (
            "You are a forensic analysis assistant. Summarize the evidence concisely. "
            "Return valid JSON with 'summary' (string) and 'key_points' (array)."
        )
        result, meta = await self._call(system_prompt, evidence_text, SummaryResult, max_tokens=max_length)
        return result

    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        system_prompt = prompt_template or (
            "You are a forensic entity extractor. Identify all entities. "
            "Return valid JSON with an 'entities' array."
        )
        result, meta = await self._call(system_prompt, evidence_text, ExtractedEntitiesResult)
        return result

    async def suggest_relationships(
        self,
        entities_context: str,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> SuggestedRelationshipsResult:
        user_prompt = f"Entities:\n{entities_context}\n\nEvidence:\n{evidence_text}"
        system_prompt = prompt_template or (
            "You are a forensic relationship analyst. Return valid JSON with "
            "a 'relationships' array."
        )
        result, meta = await self._call(system_prompt, user_prompt, SuggestedRelationshipsResult)
        return result

    async def generate_timeline(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> GeneratedTimelineResult:
        system_prompt = prompt_template or (
            "You are a forensic timeline analyst. Return valid JSON with an 'events' array."
        )
        result, meta = await self._call(system_prompt, evidence_text, GeneratedTimelineResult)
        return result

    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        system_prompt = prompt_template or (
            "You are a forensic report writer. Return valid JSON with executive_summary, "
            "evidence_summary, timeline, entities, relationships, findings, and recommendations."
        )
        result, meta = await self._call(system_prompt, investigation_context, ReportResult, max_tokens=8192)
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as exc:
            logger.warning("Ollama health check failed", error=str(exc))
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
