"""S3-compatible object storage provider.

The client is imported lazily so local development and tests do not require
cloud credentials or the boto3 package.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, BinaryIO

from app.core.config import settings
from app.storage.base import StorageProvider, StoredFile


class S3StorageProvider(StorageProvider):
    """S3-compatible storage using boto3 calls in a worker thread."""

    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("S3 storage requires boto3 to be installed") from exc

        if not settings.STORAGE_S3_BUCKET:
            raise ValueError("STORAGE_S3_BUCKET is required when STORAGE_PROVIDER=s3")
        self.bucket = settings.STORAGE_S3_BUCKET
        self.prefix = settings.STORAGE_S3_PREFIX.strip("/")
        self.client = boto3.client(
            "s3",
            region_name=settings.STORAGE_S3_REGION or None,
            endpoint_url=settings.STORAGE_S3_ENDPOINT or None,
            aws_access_key_id=settings.STORAGE_S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.STORAGE_S3_SECRET_KEY or None,
        )

    def _key(self, path: str) -> str:
        clean = path.lstrip("/")
        return f"{self.prefix}/{clean}" if self.prefix else clean

    async def store(self, data: bytes | BinaryIO, filename: str, mime_type: str, path: str | None = None) -> StoredFile:
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        safe_name = f"{uuid.uuid4().hex}_{safe_filename}"
        relative = path or f"uploads/{safe_name[:2]}/{safe_name[2:4]}"
        relative_path = f"{relative.rstrip('/')}/{safe_name}"
        payload = data if isinstance(data, bytes) else data.read()
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=self._key(relative_path),
            Body=payload,
            ContentType=mime_type,
        )
        return StoredFile(path=relative_path, filename=filename, size=len(payload), mime_type=mime_type)

    async def retrieve(self, path: str) -> bytes | None:
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=self._key(path))
            return await asyncio.to_thread(response["Body"].read)
        except self.client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
            return None

    async def delete(self, path: str) -> bool:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=self._key(path))
        return True

    async def exists(self, path: str) -> bool:
        try:
            await asyncio.to_thread(self.client.head_object, Bucket=self.bucket, Key=self._key(path))
            return True
        except self.client.exceptions.ClientError:
            return False

    async def get_size(self, path: str) -> int | None:
        try:
            response: dict[str, Any] = await asyncio.to_thread(
                self.client.head_object, Bucket=self.bucket, Key=self._key(path)
            )
            return int(response["ContentLength"])
        except self.client.exceptions.ClientError:
            return None
