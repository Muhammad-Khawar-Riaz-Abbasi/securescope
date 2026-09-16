import re
from dataclasses import dataclass
from typing import Protocol

from ..models import Document


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class LLMProvider(Protocol):
    async def answer(self, question: str, context: list[tuple[str, str]]) -> str: ...


class DeterministicEmbeddingProvider:
    async def embed(self, text: str) -> list[float]:
        buckets = [0.0] * 8
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            buckets[hash(token) % len(buckets)] += 1.0
        norm = max(sum(x * x for x in buckets) ** 0.5, 1.0)
        return [round(value / norm, 4) for value in buckets]


class DeterministicLLMProvider:
    async def answer(self, question: str, context: list[tuple[str, str]]) -> str:
        if not context:
            return "I could not find supporting evidence in this vendor's uploaded documents."
        snippets = " ".join(text for _, text in context[:3])
        return f"Based on the uploaded evidence, {snippets[:650].strip()}"


@dataclass
class RetrievedEvidence:
    document: Document
    quote: str


class EvidenceRetriever:
    def retrieve(
        self, question: str, documents: list[Document], limit: int = 3
    ) -> list[RetrievedEvidence]:
        query_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        scored: list[tuple[int, Document, str]] = []
        for document in documents:
            sentences = re.split(r"(?<=[.!?])\s+|\n+", document.content_text)
            for sentence in sentences:
                terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
                score = len(query_terms & terms)
                if score:
                    scored.append((score, document, sentence.strip()))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RetrievedEvidence(document, quote[:350]) for _, document, quote in scored[:limit]]
