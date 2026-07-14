"""
pgvector embeddings provider — concrete implementation.

Generates embeddings via the configured LLM provider and stores them
in PostgreSQL using pgvector for similarity search.

Gracefully degrades when pgvector extension is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import EmbeddingProvider, VectorStore
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding generation using OpenAI's text-embedding-3-small model."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model
        self._dimensions = dimensions
        self._client: httpx.AsyncClient | None = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                timeout=30,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        client = await self._get_client()
        body = {"model": self._model, "input": text, "dimensions": self._dimensions}
        try:
            response = await client.post("/embeddings", json=body)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except httpx.TimeoutException:
            raise TimeoutError("Embedding request timed out") from None
        except Exception as exc:
            logger.error("Embedding request failed", error=str(exc))
            raise RuntimeError(f"Embedding failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = await self._get_client()
        body = {"model": self._model, "input": texts, "dimensions": self._dimensions}
        try:
            response = await client.post("/embeddings", json=body)
            response.raise_for_status()
            data = response.json()
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]
        except httpx.TimeoutException:
            raise TimeoutError("Batch embedding request timed out") from None
        except Exception as exc:
            logger.error("Batch embedding failed", error=str(exc))
            raise RuntimeError(f"Batch embedding failed: {exc}") from exc

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class PgvectorStore(VectorStore):
    """
    pgvector-based vector store.

    Requires PostgreSQL with the pgvector extension installed.
    Gracefully returns empty results if the extension is unavailable.
    """

    TABLE_NAME = "vector_embeddings"

    async def _ensure_table(self, db: AsyncSession) -> bool:
        """Create the vector table if it doesn't exist. Returns True if ready."""
        try:
            await db.execute(
                text(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id UUID PRIMARY KEY,
                    vector vector(1536) NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """)
            )
            await db.execute(
                text(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_vector
                ON {self.TABLE_NAME} USING ivfflat (vector vector_cosine_ops)
                WITH (lists = 100)
                """)
            )
            await db.commit()
            return True
        except Exception as exc:
            logger.warning("pgvector table creation failed (extension may be missing)", error=str(exc))
            await db.rollback()
            return False

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        async with AsyncSessionLocal() as db:
            ready = await self._ensure_table(db)
            if not ready:
                return
            try:
                await db.execute(
                    text(f"""
                    INSERT INTO {self.TABLE_NAME} (id, vector, metadata)
                    VALUES (:id, :vector::vector, :metadata::jsonb)
                    ON CONFLICT (id)
                    DO UPDATE SET vector = :vector::vector, metadata = :metadata::jsonb
                    """),
                    {
                        "id": id,
                        "vector": str(vector),
                        "metadata": json.dumps(metadata),
                    },
                )
                await db.commit()
            except Exception as exc:
                logger.warning("pgvector upsert failed", error=str(exc))
                await db.rollback()

    async def search(
        self, vector: list[float], top_k: int = 10
    ) -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            ready = await self._ensure_table(db)
            if not ready:
                return []
            try:
                result = await db.execute(
                    text(f"""
                    SELECT id, metadata, 1 - (vector <=> :vector::vector) AS similarity
                    FROM {self.TABLE_NAME}
                    ORDER BY vector <=> :vector::vector
                    LIMIT :top_k
                    """),
                    {
                        "vector": str(vector),
                        "top_k": top_k,
                    },
                )
                rows = result.fetchall()
                return [
                    {
                        "id": row[0],
                        "metadata": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                        "similarity": float(row[2]) if row[2] else 0.0,
                    }
                    for row in rows
                ]
            except Exception as exc:
                logger.warning("pgvector search failed", error=str(exc))
                return []

    async def delete(self, id: str) -> None:
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(
                    text(f"DELETE FROM {self.TABLE_NAME} WHERE id = :id"),
                    {"id": id},
                )
                await db.commit()
            except Exception as exc:
                logger.warning("pgvector delete failed", error=str(exc))
                await db.rollback()

    async def health_check(self) -> bool:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                )
                return result.scalar_one_or_none() is not None
        except Exception as exc:
            logger.warning("pgvector health check failed", error=str(exc))
            return False
