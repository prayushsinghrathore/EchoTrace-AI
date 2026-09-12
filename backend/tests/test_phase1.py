"""Phase 1 regression tests for durable infrastructure providers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.models.ai_job import AIJob, AIJobStatus, AIJobType
from app.services.email_service import email_service
from app.storage.local import LocalStorageProvider


@pytest.mark.asyncio
async def test_local_storage_round_trip_and_traversal_guard(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))
    stored = await storage.store(b"evidence", "sample.txt", "text/plain")

    assert await storage.exists(stored.path)
    assert await storage.retrieve(stored.path) == b"evidence"
    assert await storage.get_size(stored.path) == 8
    assert stored.size == 8

    with pytest.raises(PermissionError):
        await storage.retrieve("../outside.txt")

    assert await storage.delete(stored.path)
    assert not await storage.exists(stored.path)


@pytest.mark.asyncio
async def test_console_email_provider_does_not_require_network() -> None:
    original = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "console"
    try:
        await email_service.send(
            to="test@example.com",
            subject="Test",
            text="This must not contact an SMTP server.",
        )
    finally:
        settings.EMAIL_PROVIDER = original


@pytest.mark.asyncio
async def test_resend_provider_uses_https_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    original_provider = settings.EMAIL_PROVIDER
    original_key = settings.RESEND_API_KEY
    calls: list[tuple[str, str, str, str | None]] = []

    async def fake_send(to: str, subject: str, text: str, html: str | None) -> None:
        calls.append((to, subject, text, html))

    monkeypatch.setattr(email_service, "_send_resend", fake_send)
    settings.EMAIL_PROVIDER = "resend"
    settings.RESEND_API_KEY = "re_test_key"
    try:
        await email_service.send(
            to="test@example.com",
            subject="Reset",
            text="Reset link",
            html="<p>Reset link</p>",
        )
    finally:
        settings.EMAIL_PROVIDER = original_provider
        settings.RESEND_API_KEY = original_key

    assert calls == [("test@example.com", "Reset", "Reset link", "<p>Reset link</p>")]


def test_ai_job_retry_metadata_is_persistable() -> None:
    job = AIJob(
        user_id=None,  # type: ignore[arg-type]
        workspace_id=None,  # type: ignore[arg-type]
        job_type=AIJobType.SUMMARIZE,
        status=AIJobStatus.QUEUED,
        attempts=0,
        provider="test",
        model="test-model",
        max_attempts=3,
    )
    assert job.status == AIJobStatus.QUEUED
    job.mark_running()
    assert job.status == AIJobStatus.RUNNING
    assert job.attempts == 1
