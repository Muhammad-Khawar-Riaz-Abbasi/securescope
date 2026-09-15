from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk


class Retriever(ABC):
    @abstractmethod
    async def retrieve(
        self, session: AsyncSession, project_id: UUID, query: str, limit: int = 3
    ) -> list[DocumentChunk]:
        """Return the most relevant evidence chunks for a project."""


class KeywordRetriever(Retriever):
    """Deterministic fallback; replace with pgvector/hybrid retrieval in production."""

    async def retrieve(
        self, session: AsyncSession, project_id: UUID, query: str, limit: int = 3
    ) -> list[DocumentChunk]:
        chunks = list(
            await session.scalars(
                select(DocumentChunk)
                .join(Document)
                .where(Document.project_id == project_id)
                .order_by(DocumentChunk.ordinal)
            )
        )
        terms = set(query.lower().split())
        return sorted(
            chunks,
            key=lambda chunk: sum(term in chunk.content.lower() for term in terms),
            reverse=True,
        )[:limit]
