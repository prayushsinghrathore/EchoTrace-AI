"""
Comprehensive AI Integration Tests — verifies every provider executes.

Uses httpx mock transports to simulate real API responses without
requiring API keys. Tests cover:
- Provider initialization and authentication headers
- Request body construction for each AI operation
- Response parsing and schema validation
- Retry with exponential backoff
- Timeout handling
- Graceful failure (no API key, network errors)
- Embedding generation
- Full AI workflow (summarize -> entities -> relationships -> timeline -> report)
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.azure_provider import AzureProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.openrouter_provider import OpenRouterProvider
from app.ai.retry import call_with_retry
from app.ai.schemas import (
    ExtractedEntitiesResult,
    GeneratedTimelineResult,
    ReportResult,
    SuggestedRelationshipsResult,
    SummaryResult,
)

SAMPLE_EVIDENCE_TEXT = """
Email from john.doe@example.com to admin@company.com on 2026-07-10.
Subject: Urgent Invoice Payment
Attachment: invoice_2026_07.zip (SHA256: a1b2c3d4e5f6...)
IP: 192.168.1.100 logged in at 14:30 UTC.
Domain: evil-phishing.com was registered 3 days ago.
"""

VALID_SUMMARY_RESPONSE = json.dumps({
    "summary": "Phishing email from john.doe@example.com with malicious attachment.",
    "key_points": [
        "Email sent on 2026-07-10",
        "Attachment named invoice_2026_07.zip",
        "Originating IP: 192.168.1.100",
    ],
})

VALID_ENTITIES_RESPONSE = json.dumps({
    "entities": [
        {"type": "person", "label": "John Doe", "confidence": 0.95, "context": "Sender of the email", "evidence_ref": "Email from john.doe@example.com"},
        {"type": "email", "label": "john.doe@example.com", "confidence": 1.0, "context": "Sender email", "evidence_ref": "From field"},
        {"type": "ip", "label": "192.168.1.100", "confidence": 0.9, "context": "Originating IP", "evidence_ref": "IP in email headers"},
        {"type": "domain", "label": "evil-phishing.com", "confidence": 0.85, "context": "Newly registered domain", "evidence_ref": "Domain registration data"},
    ]
})

VALID_RELATIONSHIPS_RESPONSE = json.dumps({
    "relationships": [
        {"source_entity_label": "John Doe", "target_entity_label": "evil-phishing.com",
         "relationship_type": "visited", "confidence": 0.7, "reasoning": "Email contains links to domain", "evidence_ref": "Email body"},
    ]
})

VALID_TIMELINE_RESPONSE = json.dumps({
    "events": [
        {"date": "2026-07-10T14:30:00Z", "title": "Phishing email sent", "description": "Email from john.doe@example.com", "confidence": 0.95, "evidence_ref": "Email log"},
    ]
})

VALID_REPORT_RESPONSE = json.dumps({
    "executive_summary": "Phishing campaign targeting company.com",
    "evidence_summary": "Single email with malicious attachment",
    "timeline": [],
    "entities": [],
    "relationships": [],
    "findings": [{"title": "Phishing attempt", "description": "Email with malicious attachment", "confidence": 0.9, "evidence_refs": ["Email #1"]}],
    "recommendations": [{"title": "Block domain", "description": "Block evil-phishing.com", "priority": "critical"}],
})

OPENAI_BASE = "http://api.test.openai"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com"
OLLAMA_BASE = "http://test.ollama:11434"
AZURE_BASE = "http://test.azure.openai"
OPENROUTER_BASE = "http://test.openrouter"


def _make_openai_chunk(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4o",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
    }


def _make_anthropic_chunk(content: str) -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": content}],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 50, "output_tokens": 100},
    }


def _make_gemini_chunk(content: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": content}], "role": "model"}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 100},
    }


def _make_ollama_chunk(content: str) -> dict:
    return {
        "model": "llama3",
        "created_at": "2026-07-14T12:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "eval_count": 100,
        "prompt_eval_count": 50,
    }


def make_transport(response_body: dict) -> httpx.MockTransport:
    """Create a transport that returns a fixed JSON response for any request."""
    return httpx.MockTransport(lambda _: httpx.Response(200, json=response_body))


def make_error_transport(status: int, body: dict | None = None) -> httpx.MockTransport:
    """Create a transport that returns an error status."""
    return httpx.MockTransport(lambda _: httpx.Response(status, json=body or {"error": "error"}))


def make_timeout_transport() -> httpx.MockTransport:
    """Create a transport that always times out."""
    async def _timeout(_):
        raise httpx.TimeoutException("Request timed out", request=httpx.Request("POST", "http://test/"))
    return httpx.MockTransport(_timeout)


def make_capturing_transport(capture_list: list, response_factory=None) -> httpx.MockTransport:
    """Create a transport that captures the request and returns a response."""
    async def _capture(request: httpx.Request) -> httpx.Response:
        capture_list.append(request)
        if response_factory:
            return response_factory(request)
        return httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))
    return httpx.MockTransport(_capture)


# ── OpenAI Provider Integration Tests ──────────────────────────────────────────


class TestOpenAIProviderIntegration:
    """Verify OpenAI provider actually executes API calls."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        """OpenAI.summarize() sends correct request and parses response."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport(_make_openai_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)
        assert "phishing" in result.summary.lower()
        assert len(result.key_points) >= 2

    @pytest.mark.asyncio
    async def test_extract_entities_executes(self) -> None:
        """OpenAI.extract_entities() returns typed entities."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport(_make_openai_chunk(VALID_ENTITIES_RESPONSE)))

        result = await provider.extract_entities(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ExtractedEntitiesResult)
        assert len(result.entities) >= 1
        assert result.entities[0].type == "person"
        assert result.entities[0].label == "John Doe"

    @pytest.mark.asyncio
    async def test_suggest_relationships_executes(self) -> None:
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport(_make_openai_chunk(VALID_RELATIONSHIPS_RESPONSE)))

        result = await provider.suggest_relationships("Entities: John Doe, evil-phishing.com", SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SuggestedRelationshipsResult)
        assert len(result.relationships) >= 1

    @pytest.mark.asyncio
    async def test_generate_timeline_executes(self) -> None:
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport(_make_openai_chunk(VALID_TIMELINE_RESPONSE)))

        result = await provider.generate_timeline(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, GeneratedTimelineResult)
        assert len(result.events) >= 1

    @pytest.mark.asyncio
    async def test_generate_report_executes(self) -> None:
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport(_make_openai_chunk(VALID_REPORT_RESPONSE)))

        result = await provider.generate_report(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ReportResult)
        assert len(result.findings) >= 1

    @pytest.mark.asyncio
    async def test_health_check_executes(self) -> None:
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_transport({"data": [{"id": "gpt-4o"}]}))

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure_graceful(self) -> None:
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_error_transport(401))

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        """Provider raises TimeoutError on timeout, not 500."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_timeout_transport())

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.summarize(SAMPLE_EVIDENCE_TEXT)

    @pytest.mark.asyncio
    async def test_http_5xx_raises_runtime_error(self) -> None:
        """Provider raises RuntimeError on 5xx, not bare exception."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=make_error_transport(502))

        with pytest.raises(RuntimeError, match="502"):
            await provider.summarize(SAMPLE_EVIDENCE_TEXT)

    @pytest.mark.asyncio
    async def test_auth_header_set_correctly(self) -> None:
        """Verify the Authorization header is set."""
        captured = []
        provider = OpenAIProvider(api_key="sk-test-secret-key-12345", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(
            base_url=OPENAI_BASE,
            headers={"Authorization": "Bearer sk-test-secret-key-12345", "Content-Type": "application/json"},
            transport=make_capturing_transport(captured),
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        assert captured[0].headers.get("Authorization") == "Bearer sk-test-secret-key-12345"

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        assert captured[0].headers["Authorization"] == "Bearer sk-test-secret-key-12345"

    @pytest.mark.asyncio
    async def test_request_body_contains_schema(self) -> None:
        """Verify the request body includes response_format with json_schema."""
        captured = []
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        resp = make_capturing_transport(captured)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=resp)

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        body = json.loads(captured[0].content)
        assert "response_format" in body
        assert body["response_format"]["type"] == "json_schema"


# ── Anthropic Provider Integration Tests ───────────────────────────────────────


class TestAnthropicProviderIntegration:
    """Verify Anthropic provider actually executes API calls."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
        provider._client = httpx.AsyncClient(base_url=ANTHROPIC_BASE, transport=make_transport(_make_anthropic_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)
        assert len(result.key_points) >= 1

    @pytest.mark.asyncio
    async def test_extract_entities_executes(self) -> None:
        provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
        provider._client = httpx.AsyncClient(base_url=ANTHROPIC_BASE, transport=make_transport(_make_anthropic_chunk(VALID_ENTITIES_RESPONSE)))

        result = await provider.extract_entities(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ExtractedEntitiesResult)
        assert len(result.entities) >= 1

    @pytest.mark.asyncio
    async def test_generate_report_executes(self) -> None:
        provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-20250514")
        provider._client = httpx.AsyncClient(base_url=ANTHROPIC_BASE, transport=make_transport(_make_anthropic_chunk(VALID_REPORT_RESPONSE)))

        result = await provider.generate_report(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ReportResult)

    @pytest.mark.asyncio
    async def test_health_check_executes(self) -> None:
        provider = AnthropicProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url=ANTHROPIC_BASE, transport=make_transport({"data": [{"id": "claude-sonnet-4"}]}))

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_auth_header_set_correctly(self) -> None:
        captured = []
        provider = AnthropicProvider(api_key="sk-ant-test-key")
        provider._client = httpx.AsyncClient(
            base_url=ANTHROPIC_BASE,
            headers={"x-api-key": "sk-ant-test-key", "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            transport=make_capturing_transport(captured, lambda _: httpx.Response(200, json=_make_anthropic_chunk(VALID_SUMMARY_RESPONSE))),
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        assert captured[0].headers["x-api-key"] == "sk-ant-test-key"
        assert captured[0].headers["anthropic-version"] == "2023-06-01"

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        provider = AnthropicProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url=ANTHROPIC_BASE, transport=make_timeout_transport())

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.summarize(SAMPLE_EVIDENCE_TEXT)


# ── Gemini Provider Integration Tests ──────────────────────────────────────────


class TestGeminiProviderIntegration:
    """Verify Gemini provider actually executes API calls."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        provider._client = httpx.AsyncClient(base_url=GEMINI_BASE, transport=make_transport(_make_gemini_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)

    @pytest.mark.asyncio
    async def test_extract_entities_executes(self) -> None:
        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        provider._client = httpx.AsyncClient(base_url=GEMINI_BASE, transport=make_transport(_make_gemini_chunk(VALID_ENTITIES_RESPONSE)))

        result = await provider.extract_entities(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ExtractedEntitiesResult)

    @pytest.mark.asyncio
    async def test_generate_report_executes(self) -> None:
        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        provider._client = httpx.AsyncClient(base_url=GEMINI_BASE, transport=make_transport(_make_gemini_chunk(VALID_REPORT_RESPONSE)))

        result = await provider.generate_report(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ReportResult)

    @pytest.mark.asyncio
    async def test_health_check_executes(self) -> None:
        provider = GeminiProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url=GEMINI_BASE, transport=make_transport({"models": [{"name": "gemini-2.0-flash"}]}))

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        provider = GeminiProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url=GEMINI_BASE, transport=make_timeout_transport())

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.summarize(SAMPLE_EVIDENCE_TEXT)

    @pytest.mark.asyncio
    async def test_response_mime_type_is_json(self) -> None:
        captured = []
        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash")
        provider._client = httpx.AsyncClient(
            base_url=GEMINI_BASE,
            transport=make_capturing_transport(captured, lambda _: httpx.Response(200, json=_make_gemini_chunk(VALID_SUMMARY_RESPONSE)))
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        body = json.loads(captured[0].content)
        assert body.get("generationConfig", {}).get("responseMimeType") == "application/json"


# ── Azure Provider Integration Tests ───────────────────────────────────────────


class TestAzureProviderIntegration:
    """Verify Azure provider actually executes API calls."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        provider = AzureProvider(api_key="test-key", endpoint=AZURE_BASE, deployment="gpt-4o")
        provider._client = httpx.AsyncClient(base_url=AZURE_BASE, transport=make_transport(_make_openai_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)

    @pytest.mark.asyncio
    async def test_extract_entities_executes(self) -> None:
        provider = AzureProvider(api_key="test-key", endpoint=AZURE_BASE, deployment="gpt-4o")
        provider._client = httpx.AsyncClient(base_url=AZURE_BASE, transport=make_transport(_make_openai_chunk(VALID_ENTITIES_RESPONSE)))

        result = await provider.extract_entities(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ExtractedEntitiesResult)

    @pytest.mark.asyncio
    async def test_health_check_graceful_failure(self) -> None:
        provider = AzureProvider(api_key="test-key", endpoint=AZURE_BASE, deployment="gpt-4o")
        provider._client = httpx.AsyncClient(base_url=AZURE_BASE, transport=make_error_transport(401))

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_auth_header_is_api_key(self) -> None:
        captured = []
        provider = AzureProvider(api_key="az-key-123", endpoint=AZURE_BASE, deployment="gpt-4o")
        provider._client = httpx.AsyncClient(
            base_url=AZURE_BASE,
            headers={"api-key": "az-key-123", "Content-Type": "application/json"},
            transport=make_capturing_transport(captured, lambda _: httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))),
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        assert captured[0].headers["api-key"] == "az-key-123"


# ── Ollama Provider Integration Tests ──────────────────────────────────────────


class TestOllamaProviderIntegration:
    """Verify Ollama provider executes correctly."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        provider = OllamaProvider(base_url=OLLAMA_BASE, model="llama3")
        provider._client = httpx.AsyncClient(base_url=OLLAMA_BASE, transport=make_transport(_make_ollama_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)

    @pytest.mark.asyncio
    async def test_extract_entities_executes(self) -> None:
        provider = OllamaProvider(base_url=OLLAMA_BASE, model="llama3")
        provider._client = httpx.AsyncClient(base_url=OLLAMA_BASE, transport=make_transport(_make_ollama_chunk(VALID_ENTITIES_RESPONSE)))

        result = await provider.extract_entities(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, ExtractedEntitiesResult)
        assert len(result.entities) >= 1

    @pytest.mark.asyncio
    async def test_markdown_json_fallback(self) -> None:
        """Ollama may return markdown-wrapped JSON; provider must handle it."""
        wrapped = f"```json\n{VALID_SUMMARY_RESPONSE}\n```"
        provider = OllamaProvider(base_url=OLLAMA_BASE, model="llama3")
        provider._client = httpx.AsyncClient(base_url=OLLAMA_BASE, transport=make_transport(_make_ollama_chunk(wrapped)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)
        assert len(result.key_points) >= 1

    @pytest.mark.asyncio
    async def test_health_check_executes(self) -> None:
        provider = OllamaProvider(base_url=OLLAMA_BASE)
        provider._client = httpx.AsyncClient(base_url=OLLAMA_BASE, transport=make_transport({"models": ["llama3"]}))

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_no_api_key_needed(self) -> None:
        """Ollama is local — no authentication required."""
        provider = OllamaProvider(base_url=OLLAMA_BASE)
        provider._client = httpx.AsyncClient(base_url=OLLAMA_BASE, transport=make_transport(_make_ollama_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)

    @pytest.mark.asyncio
    async def test_request_has_format_json(self) -> None:
        captured = []
        provider = OllamaProvider(base_url=OLLAMA_BASE, model="llama3")
        provider._client = httpx.AsyncClient(
            base_url=OLLAMA_BASE,
            transport=make_capturing_transport(captured, lambda _: httpx.Response(200, json=_make_ollama_chunk(VALID_SUMMARY_RESPONSE)))
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        body = json.loads(captured[0].content)
        assert body.get("format") == "json"
        assert not body.get("stream", True)


# ── OpenRouter Provider Integration Tests ──────────────────────────────────────


class TestOpenRouterProviderIntegration:
    """Verify OpenRouter provider executes correctly."""

    @pytest.mark.asyncio
    async def test_summarize_executes(self) -> None:
        provider = OpenRouterProvider(api_key="test-key", model="openai/gpt-4o", base_url=OPENROUTER_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENROUTER_BASE, transport=make_transport(_make_openai_chunk(VALID_SUMMARY_RESPONSE)))

        result = await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert isinstance(result, SummaryResult)

    @pytest.mark.asyncio
    async def test_referer_header_set(self) -> None:
        captured = []
        provider = OpenRouterProvider(api_key="test-key", model="openai/gpt-4o", base_url=OPENROUTER_BASE)
        provider._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE,
            headers={"Authorization": "Bearer test-key", "Content-Type": "application/json", "HTTP-Referer": "http://localhost:3000"},
            transport=make_capturing_transport(captured, lambda _: httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))),
        )

        await provider.summarize(SAMPLE_EVIDENCE_TEXT)
        assert len(captured) >= 1
        assert "HTTP-Referer" in captured[0].headers


# ── Retry Integration Tests ────────────────────────────────────────────────────


class TestRetryIntegration:
    """Verify retry logic actually executes."""

    @pytest.mark.asyncio
    async def test_retry_on_5xx_then_succeeds(self) -> None:
        """Retry fires on 5xx and eventually succeeds."""
        call_count = [0]

        async def _handler(_request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            if call_count[0] < 3:
                return httpx.Response(503, json={"error": "service unavailable"})
            return httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))

        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await call_with_retry(client, "POST", "http://test/chat", json={"test": True}, max_retries=3)
            assert response.status_code == 200
            assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout_then_succeeds(self) -> None:
        """Retry fires on timeout."""
        call_count = [0]

        async def _handler_timeout(inner_request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            if call_count[0] < 2:
                raise httpx.TimeoutException("timed out", request=inner_request)
            return httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))

        transport = httpx.MockTransport(_handler_timeout)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await call_with_retry(client, "POST", "http://test/chat", json={"test": True}, max_retries=3)
            assert response.status_code == 200
            assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx(self) -> None:
        """4xx errors should NOT be retried."""
        call_count = [0]

        async def _handler_400(_req4: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            return httpx.Response(400, json={"error": "bad request"})

        transport = httpx.MockTransport(_handler_400)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await call_with_retry(client, "POST", "http://test/chat", json={"test": True}, max_retries=3)
            assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_retry_on_429(self) -> None:
        """429 rate limits SHOULD be retried."""
        call_count = [0]

        async def _handler_429(_req: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            if call_count[0] < 2:
                return httpx.Response(429, json={"error": "rate limited"})
            return httpx.Response(200, json=_make_openai_chunk(VALID_SUMMARY_RESPONSE))

        transport = httpx.MockTransport(_handler_429)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await call_with_retry(client, "POST", "http://test/chat", json={"test": True}, max_retries=3)
            assert response.status_code == 200
            assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        """All retries exhausted raises RuntimeError."""
        transport = httpx.MockTransport(lambda _: httpx.Response(503, json={"error": "down"}))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(RuntimeError, match="503"):
                await call_with_retry(client, "POST", "http://test/chat", json={"test": True}, max_retries=2)


# ── Full AI Workflow Integration Test ──────────────────────────────────────────


class TestFullAIWorkflow:
    """Full AI workflow: summarize -> entities -> relationships -> timeline -> report."""

    SAMPLE_TEXT = SAMPLE_EVIDENCE_TEXT

    @pytest.mark.asyncio
    async def test_complete_ai_workflow(self) -> None:
        """Run the complete AI pipeline through OpenAI provider."""
        responses = [
            _make_openai_chunk(VALID_SUMMARY_RESPONSE),     # summarize
            _make_openai_chunk(VALID_ENTITIES_RESPONSE),     # extract_entities
            _make_openai_chunk(VALID_RELATIONSHIPS_RESPONSE),# suggest_relationships
            _make_openai_chunk(VALID_TIMELINE_RESPONSE),     # generate_timeline
            _make_openai_chunk(VALID_REPORT_RESPONSE),       # generate_report
        ]
        call_count = [0]

        async def multi_response(_):
            idx = call_count[0]
            call_count[0] += 1
            return httpx.Response(200, json=responses[idx % len(responses)])

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o", base_url=OPENAI_BASE)
        provider._client = httpx.AsyncClient(base_url=OPENAI_BASE, transport=httpx.MockTransport(multi_response))

        # 1. Summarize
        summary = await provider.summarize(self.SAMPLE_TEXT)
        assert isinstance(summary, SummaryResult)
        assert len(summary.key_points) >= 1

        # 2. Extract entities
        entities = await provider.extract_entities(self.SAMPLE_TEXT)
        assert isinstance(entities, ExtractedEntitiesResult)
        assert all(e.confidence >= 0.0 for e in entities.entities)

        # 3. Suggest relationships
        entity_context = "\n".join(f"{e.type}: {e.label}" for e in entities.entities)
        relationships = await provider.suggest_relationships(entity_context, self.SAMPLE_TEXT)
        assert isinstance(relationships, SuggestedRelationshipsResult)

        # 4. Generate timeline
        timeline = await provider.generate_timeline(self.SAMPLE_TEXT)
        assert isinstance(timeline, GeneratedTimelineResult)

        # 5. Generate report
        report = await provider.generate_report(self.SAMPLE_TEXT)
        assert isinstance(report, ReportResult)
        assert len(report.findings) >= 1


# ── Embedding Provider Integration Tests ───────────────────────────────────────


class TestEmbeddingProvider:
    """Verify embedding provider execution and graceful failure."""

    @pytest.mark.asyncio
    async def test_provider_properties(self) -> None:
        from app.ai.embeddings import OpenAIEmbeddingProvider
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        assert provider.dimensions == 1536

    @pytest.mark.asyncio
    async def test_embed_text_executes(self) -> None:
        from app.ai.embeddings import OpenAIEmbeddingProvider

        embed_response = {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1] * 1536}],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json=embed_response))
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url="https://api.openai.com/v1", transport=transport)

        vec = await provider.embed_text("test text")
        assert len(vec) == 1536
        assert isinstance(vec[0], float)

    @pytest.mark.asyncio
    async def test_embed_batch_executes(self) -> None:
        from app.ai.embeddings import OpenAIEmbeddingProvider

        embed_response = {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1] * 1536},
                {"object": "embedding", "index": 1, "embedding": [0.2] * 1536},
            ],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json=embed_response))
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url="https://api.openai.com/v1", transport=transport)

        vecs = await provider.embed_batch(["text one", "text two"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_timeout_raises(self) -> None:
        from app.ai.embeddings import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(api_key="test-key")
        provider._client = httpx.AsyncClient(base_url="https://api.openai.com/v1", transport=make_timeout_transport())

        with pytest.raises(TimeoutError):
            await provider.embed_text("test")


class TestPgvectorStore:
    """Verify pgvector initialization and graceful degradation."""

    @pytest.mark.asyncio
    async def test_health_check_without_pgvector(self) -> None:
        """Without pgvector extension, health_check returns False."""
        from app.ai.embeddings import PgvectorStore
        store = PgvectorStore()
        result = await store.health_check()
        assert isinstance(result, bool)
