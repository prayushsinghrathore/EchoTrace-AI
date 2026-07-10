"""
Azure OpenAI provider — interface only.

This provider is a stub prepared for future implementation.
Azure OpenAI uses a different endpoint pattern and authentication
mechanism than the standard OpenAI API.
"""

from __future__ import annotations

from app.ai.providers.base import BaseProvider
from app.ai.schemas import (
    ExtractedEntitiesResult,
    GeneratedTimelineResult,
    ReportResult,
    SuggestedRelationshipsResult,
    SummaryResult,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureProvider(BaseProvider):
    """
    Azure OpenAI provider — interface stub.

    To implement:
    1. Use azure-identity for token-based auth or direct API key
    2. Construct URL: {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}
    3. Follow the same structured output pattern as OpenAIProvider
    4. Add Azure-specific retry and rate limit handling
    """

    def __init__(self) -> None:
        logger.warning("Azure OpenAI provider is not yet implemented")

    @property
    def name(self) -> str:
        return "azure"

    @property
    def model(self) -> str:
        return "azure-openai"

    @property
    def supports_streaming(self) -> bool:
        return False

    async def summarize(
        self,
        evidence_text: str,
        max_length: int | None = None,
        prompt_template: str | None = None,
    ) -> SummaryResult:
        raise NotImplementedError("Azure OpenAI provider is not yet implemented")

    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        raise NotImplementedError("Azure OpenAI provider is not yet implemented")

    async def suggest_relationships(
        self,
        entities_context: str,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> SuggestedRelationshipsResult:
        raise NotImplementedError("Azure OpenAI provider is not yet implemented")

    async def generate_timeline(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> GeneratedTimelineResult:
        raise NotImplementedError("Azure OpenAI provider is not yet implemented")

    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        raise NotImplementedError("Azure OpenAI provider is not yet implemented")

    async def health_check(self) -> bool:
        return False
