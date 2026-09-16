import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from .models import DocumentType, ReviewStatus


class VendorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    website: HttpUrl | None = None
    owner: str | None = Field(default=None, max_length=160)
    review_deadline: datetime | None = None


class VendorPatch(BaseModel):
    review_status: ReviewStatus | None = None
    review_deadline: datetime | None = None
    owner: str | None = Field(default=None, max_length=160)


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: str
    severity: str
    title: str
    detail: str
    evidence: str
    document_id: uuid.UUID | None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    document_type: DocumentType
    content_hash: str
    extracted_at: datetime


class VendorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    website: str | None
    owner: str | None
    review_status: ReviewStatus
    review_deadline: datetime | None
    risk_score: int
    document_count: int
    finding_count: int


class VendorDetail(VendorSummary):
    documents: list[DocumentRead]
    findings: list[FindingRead]


class UploadResponse(BaseModel):
    document: DocumentRead
    findings_created: int
    duplicate: bool


class Citation(BaseModel):
    document_id: uuid.UUID
    filename: str
    quote: str


class QARequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        return " ".join(value.split())


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation]
    event_id: uuid.UUID
