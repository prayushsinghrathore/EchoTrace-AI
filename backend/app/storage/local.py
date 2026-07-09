"""Local filesystem storage provider."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.base import StorageProvider, StoredFile

logger = get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """Stores files on the local filesystem under a configurable base path."""

    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.STORAGE_LOCAL_PATH or "./storage")
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Local storage initialized", path=str(self.base_path))

    def _resolve(self, path: str) -> Path:
        # Resolve and verify the path is within base_path (traversal protection)
        full = (self.base_path / path).resolve()
        base = self.base_path.resolve()
        if not str(full).startswith(str(base)):
            raise PermissionError(f"Path traversal detected: {path}")
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    async def store(self, data: BinaryIO | bytes, filename: str, mime_type: str, path: str | None = None) -> StoredFile:
        # Sanitize filename — strip path separators to prevent traversal
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        safe_name = f"{uuid.uuid4().hex}_{safe_filename}"
        relative = path or f"uploads/{safe_name[:2]}/{safe_name[2:4]}"
        file_path = relative + "/" + safe_name
        full = self._resolve(file_path)

        if isinstance(data, bytes):
            full.write_bytes(data)
        else:
            data.seek(0)
            full.write_bytes(data.read())
        size = full.stat().st_size

        logger.debug("File stored", path=file_path, size=size, mime=mime_type)
        return StoredFile(path=file_path, filename=filename, size=size, mime_type=mime_type)

    async def retrieve(self, path: str) -> bytes | None:
        full = self._resolve(path)
        if not full.exists():
            return None
        return full.read_bytes()

    async def delete(self, path: str) -> bool:
        full = self._resolve(path)
        if full.exists():
            full.unlink()
            logger.debug("File deleted", path=path)
            return True
        return False

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    async def get_size(self, path: str) -> int | None:
        full = self._resolve(path)
        if full.exists():
            return full.stat().st_size
        return None
