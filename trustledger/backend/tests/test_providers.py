import pytest

from app.services.ai import DeterministicEmbeddingProvider, DeterministicLLMProvider
from app.services.ingest import extract_findings


@pytest.mark.asyncio
async def test_embedding_is_deterministic_shape():
    provider = DeterministicEmbeddingProvider()
    assert await provider.embed("same input") == await provider.embed("same input")
    assert len(await provider.embed("same input")) == 8


@pytest.mark.asyncio
async def test_local_llm_requires_evidence():
    provider = DeterministicLLMProvider()
    assert "could not find" in await provider.answer("question", [])
    assert "evidence" in await provider.answer("question", [("a.txt", "Evidence is here")])


def test_rules_extract_explainable_findings():
    findings = extract_findings(
        "The supplier may use a subprocessor without notice and has SOC 2 certification."
    )
    assert {finding.severity for finding in findings} == {"high", "low"}
    assert all(finding.evidence for finding in findings)
