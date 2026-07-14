"""
Google Gemini LLM provider.

Uses the Gemini API via HTTP for structured output generation.
Supports configurable model and timeout.
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

MODEL_COST_MAP: dict[str, dict[str, float]] = {
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    "gemini-2.0-flash-lite": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}


class GeminiProvider(BaseProvider):
    """LLM provider using the Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL
        self._client: httpx.AsyncClient | None = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        return self._client

    def _build_url(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )

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
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {"parts": [{"text": user_prompt}]},
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens or settings.AI_MAX_TOKENS,
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = await client.post(self._build_url(), json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise TimeoutError(f"Gemini request timed out after {settings.AI_TIMEOUT_SECONDS}s") from None
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API error", status=exc.response.status_code, body=exc.response.text)
            raise RuntimeError(f"Gemini API error: {exc.response.status_code}") from exc

        elapsed = int((time.time() - start) * 1000)

        # Extract usage
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        # Extract text from response
        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                content = parts[0].get("text", "")

        # Parse JSON (Gemini supports responseMimeType: application/json)
        try:
            parsed = json.loads(content)
            result = response_schema.model_validate(parsed)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini returned invalid JSON: {content[:300]}") from exc
        except ValueError as exc:
            raise ValueError(f"LLM output failed schema validation: {exc}") from exc

        cost = self._estimate_cost(input_tokens, output_tokens)

        usage_meta = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": elapsed,
        }

        return result, usage_meta

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COST_MAP.get(self._model, {"input": 0.0001, "output": 0.0004})
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
        result, meta = await self._call(system_prompt, evidence_text, SummaryResult, max_tokens=max_length)
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
            "'relationships' array."
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
            "the provided evidence. Return a JSON object with an 'events' array."
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
        try:
            client = await self._get_client()
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self._api_key}"
            response = await client.get(url)
            return response.status_code == 200
        except Exception as exc:
            logger.warning("Gemini health check failed", error=str(exc))
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
