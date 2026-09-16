import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedFinding:
    category: str
    severity: str
    title: str
    detail: str
    evidence: str


RULES = [
    (
        "security",
        "high",
        "Breach notification window is broad",
        r"(?:notify|notification).{0,80}(?:30|sixty|60).{0,30}day|(?:30|sixty|60).{0,30}day.{0,40}(?:breach|notification)",
        "The document allows a notification period of 30 days or more.",
    ),
    (
        "privacy",
        "high",
        "Subprocessor approval is not explicit",
        r"subprocessor.{0,80}(?:may|without).{0,50}(?:notice|consent)",
        "Subprocessor use appears possible without clear prior approval.",
    ),
    (
        "resilience",
        "medium",
        "Business continuity evidence requested",
        r"business continuity|disaster recovery|recovery point",
        "Business continuity language is present and should be validated with evidence.",
    ),
    (
        "contract",
        "medium",
        "Auto-renewal clause detected",
        r"auto(?:matic|matically)? renew|renewal",
        "An automatic renewal clause was detected.",
    ),
    (
        "security",
        "low",
        "Security certification referenced",
        r"soc 2|iso 27001|security certification",
        "A security certification is referenced; validate scope and expiry.",
    ),
]


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def extract_text(filename: str, content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200_000]


def classify_document(filename: str) -> str:
    lower = filename.lower()
    if any(word in lower for word in ("contract", "agreement", "msa", "terms")):
        return "contract"
    if any(word in lower for word in ("questionnaire", "sig", "security")):
        return "questionnaire"
    if "policy" in lower:
        return "policy"
    return "other"


def extract_findings(text: str) -> list[ExtractedFinding]:
    findings: list[ExtractedFinding] = []
    for category, severity, title, pattern, detail in RULES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(match.start() - 90, 0)
            evidence = text[start : min(match.end() + 130, len(text))].strip()
            findings.append(ExtractedFinding(category, severity, title, detail, evidence))
    return findings
