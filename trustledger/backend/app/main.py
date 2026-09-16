import json
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_session, init_db
from .deps import verify_api_key
from .models import Document, DocumentType, Finding, QAEvent, Vendor
from .schemas import (
    Citation,
    DocumentRead,
    QARequest,
    QAResponse,
    UploadResponse,
    VendorCreate,
    VendorDetail,
    VendorPatch,
    VendorSummary,
)
from .services.ai import DeterministicLLMProvider, EvidenceRetriever
from .services.ingest import classify_document, content_hash, extract_findings, extract_text

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id = request.headers.get(settings.request_id_header, str(uuid.uuid4()))
    response = await call_next(request)
    response.headers[settings.request_id_header] = request_id
    return response


def risk_score(findings: list[Finding]) -> int:
    penalties = {"high": 22, "medium": 10, "low": 4}
    return max(0, 100 - min(100, sum(penalties.get(item.severity, 0) for item in findings)))


def to_summary(vendor: Vendor) -> VendorSummary:
    return VendorSummary(
        id=vendor.id,
        name=vendor.name,
        website=vendor.website,
        owner=vendor.owner,
        review_status=vendor.review_status,
        review_deadline=vendor.review_deadline,
        risk_score=risk_score(vendor.findings),
        document_count=len(vendor.documents),
        finding_count=len(vendor.findings),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/vendors", response_model=list[VendorSummary], dependencies=[Depends(verify_api_key)])
async def list_vendors(
    session: AsyncSession = Depends(get_session),
    search: str | None = Query(default=None, max_length=100),
):
    result = await session.execute(select(Vendor).order_by(Vendor.updated_at.desc()))
    vendors = list(result.scalars().unique())
    if search:
        vendors = [vendor for vendor in vendors if search.lower() in vendor.name.lower()]
    return [to_summary(vendor) for vendor in vendors]


@app.post(
    "/api/vendors",
    response_model=VendorSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
async def create_vendor(payload: VendorCreate, session: AsyncSession = Depends(get_session)):
    vendor = Vendor(
        name=payload.name.strip(),
        website=str(payload.website) if payload.website else None,
        owner=payload.owner,
        review_deadline=payload.review_deadline,
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)
    return to_summary(vendor)


@app.get(
    "/api/vendors/{vendor_id}", response_model=VendorDetail, dependencies=[Depends(verify_api_key)]
)
async def get_vendor(vendor_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return VendorDetail(
        **to_summary(vendor).model_dump(),
        documents=[DocumentRead.model_validate(doc) for doc in vendor.documents],
        findings=vendor.findings,
    )


@app.patch(
    "/api/vendors/{vendor_id}", response_model=VendorSummary, dependencies=[Depends(verify_api_key)]
)
async def patch_vendor(
    vendor_id: uuid.UUID, payload: VendorPatch, session: AsyncSession = Depends(get_session)
):
    vendor = (
        await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    ).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, key, value)
    await session.commit()
    await session.refresh(vendor)
    return to_summary(vendor)


@app.post(
    "/api/vendors/{vendor_id}/documents",
    response_model=UploadResponse,
    dependencies=[Depends(verify_api_key)],
)
async def upload_document(
    vendor_id: uuid.UUID, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)
):
    vendor = (
        await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    ).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds configured size limit")
    if not content:
        raise HTTPException(status_code=400, detail="Document is empty")
    digest = content_hash(content)
    duplicate = (
        await session.execute(
            select(Document).where(Document.vendor_id == vendor_id, Document.content_hash == digest)
        )
    ).scalar_one_or_none()
    if duplicate:
        return UploadResponse(document=duplicate, findings_created=0, duplicate=True)
    text = extract_text(file.filename or "document.txt", content)
    document = Document(
        vendor_id=vendor_id,
        filename=(file.filename or "document.txt")[:255],
        document_type=DocumentType(classify_document(file.filename or "")),
        content_hash=digest,
        content_text=text,
    )
    session.add(document)
    await session.flush()
    findings = extract_findings(text)
    for finding in findings:
        session.add(
            Finding(
                vendor_id=vendor_id,
                document_id=document.id,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                detail=finding.detail,
                evidence=finding.evidence,
            )
        )
    await session.commit()
    await session.refresh(document)
    return UploadResponse(document=document, findings_created=len(findings), duplicate=False)


@app.post(
    "/api/vendors/{vendor_id}/ask",
    response_model=QAResponse,
    dependencies=[Depends(verify_api_key)],
)
async def ask_vendor(
    vendor_id: uuid.UUID, payload: QARequest, session: AsyncSession = Depends(get_session)
):
    vendor = (
        await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    ).scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    evidence = EvidenceRetriever().retrieve(payload.question, vendor.documents)
    context = [(item.document.filename, item.quote) for item in evidence]
    answer = await DeterministicLLMProvider().answer(payload.question, context)
    citations = [
        Citation(document_id=item.document.id, filename=item.document.filename, quote=item.quote)
        for item in evidence
    ]
    event = QAEvent(
        vendor_id=vendor_id,
        question=payload.question,
        answer=answer,
        citations=json.dumps([item.model_dump(mode="json") for item in citations]),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return QAResponse(answer=answer, citations=citations, event_id=event.id)


@app.exception_handler(Exception)
async def safe_errors(_, exc: Exception):
    if settings.environment == "development":
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
