"""
Azure OpenAI LLM provider.

Connects to Azure OpenAI Service using the deployment-based endpoint pattern.
Uses direct HTTP for structured output generation.
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
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
}


class AzureProvider(BaseProvider):
    """LLM provider using Azure OpenAI Service."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.AZURE_OPENAI_KEY
        self._endpoint = (endpoint or settings.AZURE_OPENAI_ENDPOINT).rstrip("/")
        self._deployment = deployment or settings.AZURE_OPENAI_DEPLOYMENT
        self._api_version = api_version or settings.AZURE_OPENAI_API_VERSION
        self._client: httpx.AsyncClient | None = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def name(self) -> str:
        return "azure"

    @property
    def model(self) -> str:
        return self._deployment or "gpt-4o"

    @property
    def supports_streaming(self) -> bool:
        return False

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._endpoint,
                timeout=settings.AI_TIMEOUT_SECONDS,
                headers={
                    "api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _build_url(self) -> str:
        return (
            f"/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={self._api_version}"
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

        schema = response_schema.model_json_schema()
        schema_name = response_schema.__name__

        body: dict[str, Any] = {
            "model": self._deployment,
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
            response = await client.post(self._build_url(), json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Azure request timed out after {settings.AI_TIMEOUT_SECONDS}s"
            ) from None
        except httpx.HTTPStatusError as exc:
            logger.error("Azure API error", status=exc.response.status_code, body=exc.response.text)
            raise RuntimeError(f"Azure API error: {exc.response.status_code}") from exc

        elapsed = int((time.time() - start) * 1000)

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
            result = response_schema.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Azure LLM returned invalid JSON: {exc}") from exc

        cost = self._estimate_cost(input_tokens, output_tokens)

        usage_meta = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": elapsed,
        }

        return result, usage_meta

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        model_name = self._deployment or "gpt-4o"
        costs = next(
            (c for k, c in MODEL_COST_MAP.items() if k in model_name),
            {"input": 0.0025, "output": 0.01},
        )
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
        result, meta = await self._call(
            system_prompt, evidence_text, SummaryResult, max_tokens=max_length
        )
        return result

    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        system_prompt = prompt_template or (
            "You are a forensic entity extractor. Identify all relevant entities "
            "from the provided evidence. Return a JSON object with an 'entities' array."
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
            "You are a forensic relationship analyst. Return a JSON object with "
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
            "You are a forensic timeline analyst. Return a JSON object with an 'events' array."
        )
        result, meta = await self._call(system_prompt, evidence_text, GeneratedTimelineResult)
        return result

    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        system_prompt = prompt_template or (
            "You are a forensic report writer. Return a JSON object with executive_summary, "
            "evidence_summary, timeline, entities, relationships, findings, and recommendations."
        )
        result, meta = await self._call(
            system_prompt, investigation_context, ReportResult, max_tokens=8192
        )
        return result

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(f"/openai/models?api-version={self._api_version}")
            return response.status_code == 200
        except Exception as exc:
            logger.warning("Azure health check failed", error=str(exc))
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
