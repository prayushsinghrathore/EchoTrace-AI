"""
Configurable maximum request body size middleware.

Rejects incoming requests whose Content-Length exceeds the configured
limit with a 413 Payload Too Large response. Protects against oversized
payload attacks without breaking valid uploads.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that rejects requests exceeding MAX_REQUEST_BODY_SIZE.

    Checks the Content-Length header before the request body is read,
    avoiding unnecessary I/O on oversized payloads.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length_str = request.headers.get("content-length")
        max_size = settings.MAX_REQUEST_BODY_SIZE

        if content_length_str is not None:
            try:
                content_length = int(content_length_str)
                if content_length > max_size:
                    logger.warning(
                        "Request body too large",
                        content_length=content_length,
                        max_size=max_size,
                        path=str(request.url.path),
                        method=request.method,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Request body too large. "
                                f"Maximum allowed size is {max_size} bytes "
                                f"({max_size // 1024 // 1024} MB)."
                            ),
                            "request_size": content_length,
                            "max_allowed": max_size,
                        },
                    )
            except (ValueError, TypeError):
                pass

        return await call_next(request)


def add_body_size_limit_middleware(app: FastAPI) -> None:
    """
    Register the request body size limit middleware.
    Added early in the middleware stack so oversized requests are
    rejected before reaching other middleware or route handlers.
    """
    app.add_middleware(RequestBodySizeLimitMiddleware)
    logger.debug(
        "Body size limit middleware enabled",
        max_bytes=settings.MAX_REQUEST_BODY_SIZE,
    )
