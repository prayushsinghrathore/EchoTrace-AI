"""Transactional email delivery with safe development behavior."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Send transactional email through SMTP or log it in console mode."""

    async def send(self, *, to: str, subject: str, text: str, html: str | None = None) -> None:
        if settings.EMAIL_PROVIDER == "console":
            logger.info("Email delivery (console)", extra={"to": to, "subject": subject, "body": text})
            return
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._send_smtp, to, subject, text, html),
                timeout=settings.EMAIL_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception(
                "SMTP email delivery failed",
                to=to,
                subject=subject,
                smtp_host=settings.SMTP_HOST,
                smtp_port=settings.SMTP_PORT,
            )
            raise
        logger.info(
            "SMTP email accepted by server",
            to=to,
            subject=subject,
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
        )

    def _send_smtp(self, to: str, subject: str, text: str, html: str | None) -> None:
        message = EmailMessage()
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text)
        if html:
            message.add_alternative(html, subtype="html")

        smtp_class = smtplib.SMTP_SSL if settings.SMTP_USE_TLS else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.EMAIL_TIMEOUT_SECONDS) as client:
            if settings.SMTP_USE_STARTTLS:
                client.starttls()
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)


email_service = EmailService()
