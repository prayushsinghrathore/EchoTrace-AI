"""
Compression middleware for EchoTrace AI.

Adds gzip/brotli response compression to reduce bandwidth and improve
load times. Implemented as optional ASGI middleware using Starlette's
built-in GZipMiddleware. No external dependencies required.
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings


def add_compression_middleware(app: FastAPI) -> None:
    """
    Add gzip compression middleware to the application.

    Compresses responses >= 1000 bytes at the default compression level.
    Browsers that support gzip will receive compressed responses transparently.
    """
    minimum_size = settings.COMPRESSION_MINIMUM_SIZE

    app.add_middleware(
        GZipMiddleware,
        minimum_size=minimum_size,
    )
