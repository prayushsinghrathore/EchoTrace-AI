"""
OpenRouter LLM provider.

API-compatible with OpenAI but routes through OpenRouter for access
to multiple models. Supports the same structured output pattern.
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


class OpenRouterProvider(BaseProvider):
    """LLM provider using the OpenRouter API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENROUTER_API_KEY
        self._model = model or settings.OPENROUTER_MODEL
        self._base_url = base_url or settings.OPENROUTER_BASE_URL
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "openrouter"

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
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else "http://localhost:3000",
                },
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
            "max_tokens": max_tokens or settings.AI_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await client.post("/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise TimeoutError(f"OpenRouter request timed out after {settings.AI_TIMEOUT_SECONDS}s") from None
        except httpx.HTTPStatusError as exc:
            logger.error("OpenRouter API error", status=exc.response.status_code, body=exc.response.text)
            raise RuntimeError(f"OpenRouter API error: {exc.response.status_code}") from exc

        elapsed = int((time.time() - start) * 1000)

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
            result = response_schema.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse structured LLM output", error=str(exc))
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        cost = 0.0  # OpenRouter provides cost in response headers/body
        if "native_tokens" in data:
            cost = (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60

        usage_meta = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
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
            "You are a forensic analysis assistant. Summarize the provided evidence "
            "clearly and concisely. Return JSON with 'summary' (string) "
            "and 'key_points' (array of strings)."
        )
        result, meta = await self._call(system_prompt, evidence_text, SummaryResult, max_tokens=max_length)
        return result

    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        system_prompt = prompt_template or (
            "You are a forensic entity extractor. Identify all relevant entities "
            "from the provided evidence. Return JSON with an 'entities' array."
        )
        result, meta = await self._call(system_prompt, evidence_text, ExtractedEntitiesResult)
        return result

    async def suggest_relationships(
        self,
        entities_context: str,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> SuggestedRelationshipsResult:
        user_prompt = (
            f"Entities:\n{entities_context}\n\nEvidence:\n{evidence_text}"
        )
        system_prompt = prompt_template or (
            "You are a forensic relationship analyst. Suggest relationships "
            "between entities. Return JSON with a 'relationships' array."
        )
        result, meta = await self._call(system_prompt, user_prompt, SuggestedRelationshipsResult)
        return result

    async def generate_timeline(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> GeneratedTimelineResult:
        system_prompt = prompt_template or (
            "You are a forensic timeline analyst. Extract chronological events. "
            "Return JSON with an 'events' array."
        )
        result, meta = await self._call(system_prompt, evidence_text, GeneratedTimelineResult)
        return result

    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        system_prompt = prompt_template or (
            "You are a forensic investigation report writer. Generate a complete "
            "report. Return JSON with executive_summary, evidence_summary, timeline, "
            "entities, relationships, findings, and recommendations."
        )
        result, meta = await self._call(system_prompt, investigation_context, ReportResult, max_tokens=8192)
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/models", params={"limit": 1})
            return response.status_code == 200
        except Exception as exc:
            logger.warning("OpenRouter health check failed", error=str(exc))
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
