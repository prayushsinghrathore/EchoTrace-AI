"""Storage provider factory."""

from app.core.config import settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider


def create_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    if settings.STORAGE_PROVIDER == "s3":
        from app.storage.s3 import S3StorageProvider
        return S3StorageProvider()
    raise ValueError(f"Unsupported STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")
