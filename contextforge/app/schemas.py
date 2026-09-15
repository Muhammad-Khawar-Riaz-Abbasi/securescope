from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TenantOut(TenantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class ProjectCreate(BaseModel):
    tenant_id: UUID
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime


class IncidentCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20_000)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    description: str
    status: str
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1_000_000)

    @field_validator("content")
    @classmethod
    def reject_control_content(cls, value: str) -> str:
        if any(ord(char) < 9 for char in value):
            raise ValueError("content contains unsupported control characters")
        return value


class Citation(BaseModel):
    document_id: UUID
    title: str
    chunk_id: UUID
    excerpt: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2_000)


class AskResponse(BaseModel):
    answer: str
    confidence: float = Field(ge=0, le=1)
    uncertainty: list[str]
    citations: list[Citation]
