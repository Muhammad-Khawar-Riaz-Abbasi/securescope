import hashlib
import re
from dataclasses import dataclass


class Embedder:
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class LLM:
    async def answer(self, question: str, evidence: list[str]) -> str:
        raise NotImplementedError


class DeterministicEmbedder(Embedder):
    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [round(byte / 255, 6) for byte in digest[:8]]


class DeterministicLLM(LLM):
    async def answer(self, question: str, evidence: list[str]) -> str:
        if not evidence:
            return "I could not find enough project evidence to answer this question."
        return f"Based on the indexed evidence: {evidence[0][:500]}"


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    content: str


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[Chunk]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks: list[Chunk] = []
    step = size - overlap
    for ordinal, start in enumerate(range(0, len(words), step)):
        content = " ".join(words[start : start + size])
        chunks.append(Chunk(ordinal=ordinal, content=content))
        if start + size >= len(words):
            break
    return chunks
