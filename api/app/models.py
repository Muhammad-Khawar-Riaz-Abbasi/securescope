from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    context: list[str] = Field(default_factory=list, max_length=12)


class Finding(BaseModel):
    code: str
    severity: Literal["high", "medium", "low", "positive"]
    title: str
    detail: str


class AnalyzeResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    label: Literal["critical", "weak", "fair", "strong", "excellent"]
    entropy_bits: float
    length: int
    breached: bool
    breach_count: int
    findings: list[Finding]
