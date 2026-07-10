"""
Abstract LLM provider interface.

All AI providers (OpenAI, OpenRouter, Ollama, Azure) implement this
interface. The AIService selects the appropriate provider based on
configuration and delegates all LLM calls through this abstraction.
"""

from __future__ import annotations

import abc
from typing import Any

from app.ai.schemas import (
    ExtractedEntitiesResult,
    GeneratedTimelineResult,
    ReportResult,
    SuggestedRelationshipsResult,
    SummaryResult,
)


class BaseProvider(abc.ABC):
    """
    Abstract interface for LLM providers.

    Each provider implements AI operations for a specific backend
    (OpenAI, OpenRouter, Ollama, Azure). Providers handle prompt
    construction, API calls, retries, and structured output parsing.
    """

    @abc.abstractmethod
    async def summarize(
        self,
        evidence_text: str,
        max_length: int | None = None,
        prompt_template: str | None = None,
    ) -> SummaryResult:
        """Summarize evidence text and return key points."""
        ...

    @abc.abstractmethod
    async def extract_entities(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> ExtractedEntitiesResult:
        """Extract entities from evidence text."""
        ...

    @abc.abstractmethod
    async def suggest_relationships(
        self,
        entities_context: str,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> SuggestedRelationshipsResult:
        """Suggest relationships between entities based on evidence."""
        ...

    @abc.abstractmethod
    async def generate_timeline(
        self,
        evidence_text: str,
        prompt_template: str | None = None,
    ) -> GeneratedTimelineResult:
        """Generate chronological timeline from evidence."""
        ...

    @abc.abstractmethod
    async def generate_report(
        self,
        investigation_context: str,
        prompt_template: str | None = None,
    ) -> ReportResult:
        """Generate a complete investigation report."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verify provider connectivity and return True if healthy."""
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'openai', 'openrouter')."""
        ...

    @property
    @abc.abstractmethod
    def model(self) -> str:
        """Current model identifier (e.g. 'gpt-4o')."""
        ...

    @property
    @abc.abstractmethod
    def supports_streaming(self) -> bool:
        """Whether the provider supports response streaming."""
        ...

    def get_usage_summary(self) -> dict[str, Any]:
        """Return current usage statistics for this provider."""
        return {}


class EmbeddingProvider(abc.ABC):
    """
    Abstract interface for embedding generation.

    Prepare for future vector search and RAG capabilities.
    Not yet implemented — reserved for future use.
    """

    @abc.abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a text string."""
        ...

    @abc.abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        ...

    @property
    @abc.abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...


class VectorStore(abc.ABC):
    """
    Abstract interface for vector storage and similarity search.

    Prepare for future RAG capabilities.
    Not yet implemented — reserved for future use.
    """

    @abc.abstractmethod
    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        """Insert or update a vector entry."""
        ...

    @abc.abstractmethod
    async def search(self, vector: list[float], top_k: int = 10) -> list[dict]:
        """Find the top_k most similar vectors."""
        ...

    @abc.abstractmethod
    async def delete(self, id: str) -> None:
        """Delete a vector entry."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity to the vector store."""
        ...
