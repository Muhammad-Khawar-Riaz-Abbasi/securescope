import pytest

from app.providers import DeterministicEmbedder, chunk_text


def test_chunking_is_deterministic_and_bounded():
    chunks = chunk_text(" ".join(f"word{i}" for i in range(1000)), size=20, overlap=3)
    assert chunks[0].ordinal == 0
    assert len(chunks) > 1
    assert all(len(chunk.content.split()) <= 20 for chunk in chunks)


@pytest.mark.asyncio
async def test_mock_embedding_is_stable():
    embedder = DeterministicEmbedder()
    assert await embedder.embed("same") == await embedder.embed("same")
    assert await embedder.embed("same") != await embedder.embed("different")
