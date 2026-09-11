import hashlib
import math
import re

from .models import AnalyzeResponse, Finding

COMMON_PASSWORDS = {
    "password",
    "password123",
    "123456",
    "12345678",
    "qwerty",
    "letmein",
    "welcome",
    "admin",
    "iloveyou",
}


def _entropy(password: str) -> float:
    alphabet = 0
    if re.search(r"[a-z]", password):
        alphabet += 26
    if re.search(r"[A-Z]", password):
        alphabet += 26
    if re.search(r"\d", password):
        alphabet += 10
    if re.search(r"[^A-Za-z0-9]", password):
        alphabet += 33
    return round(len(password) * math.log2(alphabet), 1) if alphabet else 0.0


def _has_sequence(password: str) -> bool:
    lowered = password.lower()
    sequences = ("1234", "2345", "3456", "abcd", "qwerty", "asdf")
    return any(sequence in lowered or sequence[::-1] in lowered for sequence in sequences)


def analyze_password(password: str, context: list[str] | None = None) -> AnalyzeResponse:
    context = [item.strip().lower() for item in (context or []) if item.strip()]
    normalized = password.lower()
    findings: list[Finding] = []
    score = 100

    if len(password) < 12:
        score -= 30
        findings.append(Finding(
            code="short",
            severity="high",
            title="Use at least 12 characters",
            detail="Long passphrases resist guessing better than short, complex-looking passwords.",
        ))
    elif len(password) >= 16:
        findings.append(Finding(
            code="length",
            severity="positive",
            title="Strong length",
            detail="A password of 16 or more characters gives you a solid baseline.",
        ))

    if password.lower() in COMMON_PASSWORDS:
        score -= 55
        findings.append(Finding(
            code="common",
            severity="high",
            title="This is a commonly used password",
            detail="Attackers try popular passwords first. Replace it immediately.",
        ))

    if context and any(token in normalized for token in context if len(token) >= 3):
        score -= 25
        findings.append(Finding(
            code="context",
            severity="high",
            title="Avoid personal details",
            detail="Names, usernames, IDs, and dates connected to you are easy to target.",
        ))

    if _has_sequence(password):
        score -= 15
        findings.append(Finding(
            code="sequence",
            severity="medium",
            title="Predictable sequence detected",
            detail="Keyboard and alphabetical sequences are common guesses.",
        ))

    if len(set(password)) <= max(3, len(password) // 3):
        score -= 15
        findings.append(Finding(
            code="repetition",
            severity="medium",
            title="Too much character repetition",
            detail="Repeated characters reduce the effective search space.",
        ))

    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        score -= 8
    if not re.search(r"\d", password):
        score -= 8
    if not re.search(r"[^A-Za-z0-9]", password):
        score -= 8

    return AnalyzeResponse(
        score=max(0, min(100, score)),
        label=_label(score),
        entropy_bits=_entropy(password),
        length=len(password),
        breached=False,
        breach_count=0,
        findings=findings,
    )


def _label(score: int) -> str:
    if score < 25:
        return "critical"
    if score < 50:
        return "weak"
    if score < 70:
        return "fair"
    if score < 90:
        return "strong"
    return "excellent"


def sha1_prefix(password: str) -> tuple[str, str]:
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    return digest[:5], digest[5:]
