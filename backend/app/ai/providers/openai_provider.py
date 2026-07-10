"""
OpenAI LLM provider.

Uses the OpenAI Python SDK with structured outputs for validated JSON.
Supports configurable model, base URL, and timeout.
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

# Cost per 1K tokens (approximate, model-dependent)
MODEL_COST_MAP: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


class OpenAIProvider(BaseProvider):
    """LLM provider using the OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        self._base_url = base_url or settings.OPENAI_BASE_URL
        self._client: httpx.AsyncClient | None = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def name(self) -> str:
        return "openai"

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
        """
        Call the OpenAI chat completions API with structured output.

        Returns:
            Tuple of (parsed response object, usage metadata).
        """
        client = await self._get_client()
        start = time.time()

        schema = response_schema.model_json_schema()
        schema_name = response_schema.__name__

        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens or settings.AI_MAX_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        }

        try:
            response = await client.post("/chat/completions", json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise TimeoutError(f"OpenAI request timed out after {settings.AI_TIMEOUT_SECONDS}s") from None
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI API error", status=exc.response.status_code, body=exc.response.text)
            raise RuntimeError(f"OpenAI API error: {exc.response.status_code}") from exc

        elapsed = int((time.time() - start) * 1000)

        # Extract usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        # Extract structured output
        choice = data["choices"][0]
        content = choice["message"]["content"]

        try:
            parsed = json.loads(content)
            result = response_schema.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse structured LLM output", error=str(exc), content=content[:200])
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        cost = self._estimate_cost(input_tokens, output_tokens)

        usage_meta = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": elapsed,
        }

        return result, usage_meta

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost based on model pricing."""
        costs = MODEL_COST_MAP.get(self._model, {"input": 0.002, "output": 0.008})
        return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])

    def get_usage_summary(self) -> dict[str, Any]:
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }

    async def summarize(
        self,
        evidence_text: str,
        max_length: int | None = None,
        prompt_template: str | None = None,
    ) -> SummaryResult:
        system_prompt = prompt_template or (
            "You are a forensic analysis assistant. Summarize the provided evidence "
            "clearly and concisely. Return a JSON object with 'summary' (string) "
            "and 'key_points' (array of strings)."
        )
        result, _meta = await self._call(system_prompt, evidence_text, SummaryResult, max_tokens=max_length)
        return result

    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        system_prompt = prompt_template or (
            "You are a forensic entity extractor. Identify all relevant entities "
            "from the provided evidence. Return a JSON object with an 'entities' "
            "array containing objects with 'type', 'label', 'confidence', 'context', "
            "and 'evidence_ref' fields."
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
            f"Entities identified in this investigation:\n{entities_context}\n\n"
            f"Evidence text:\n{evidence_text}\n\n"
            "Based on the above, suggest relationships between entities."
        )
        system_prompt = prompt_template or (
            "You are a forensic relationship analyst. Suggest relationships between "
            "entities based on the provided evidence. Return a JSON object with a "
            "'relationships' array containing objects with 'source_entity_label', "
            "'target_entity_label', 'relationship_type', 'confidence', 'reasoning', "
            "and 'evidence_ref' fields."
        )
        result, meta = await self._call(system_prompt, user_prompt, SuggestedRelationshipsResult)
        return result

    async def generate_timeline(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> GeneratedTimelineResult:
        system_prompt = prompt_template or (
            "You are a forensic timeline analyst. Extract chronological events from "
            "the provided evidence. Return a JSON object with an 'events' array "
            "containing objects with 'date', 'title', 'description', 'confidence', "
            "and 'evidence_ref' fields."
        )
        result, meta = await self._call(system_prompt, evidence_text, GeneratedTimelineResult)
        return result

    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        system_prompt = prompt_template or (
            "You are a forensic investigation report writer. Generate a comprehensive "
            "investigation report from the provided context. Return a JSON object with "
            "'executive_summary', 'evidence_summary', 'timeline', 'entities', "
            "'relationships', 'findings', and 'recommendations' fields."
        )
        result, meta = await self._call(system_prompt, investigation_context, ReportResult, max_tokens=8192)
        return result

    async def health_check(self) -> bool:
        """Verify provider connectivity by listing models."""
        try:
            client = await self._get_client()
            response = await client.get("/models", params={"limit": 1})
            return response.status_code == 200
        except Exception as exc:
            logger.warning("OpenAI health check failed", error=str(exc))
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
