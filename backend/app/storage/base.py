"""Abstract storage provider interface."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class StoredFile:
    path: str
    filename: str
    size: int
    mime_type: str


class StorageProvider(abc.ABC):
    """Interface for file storage backends."""

    @abc.abstractmethod
    async def store(self, data: bytes | BinaryIO, filename: str, mime_type: str, path: str | None = None) -> StoredFile:
        ...

    @abc.abstractmethod
    async def retrieve(self, path: str) -> bytes | None:
        ...

    @abc.abstractmethod
    async def delete(self, path: str) -> bool:
        ...

    @abc.abstractmethod
    async def exists(self, path: str) -> bool:
        ...

    @abc.abstractmethod
    async def get_size(self, path: str) -> int | None:
        ...
