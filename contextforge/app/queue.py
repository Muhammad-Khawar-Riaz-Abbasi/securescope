class IngestionQueue:
    """Async boundary for Redis/Celery/etc.; the MVP indexes in-process safely."""

    async def enqueue(self, document_id: str) -> None:
        return None
