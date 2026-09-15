import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import Database
from app.models import Document, DocumentChunk, Incident, Project, Tenant
from app.providers import DeterministicEmbedder, DeterministicLLM, chunk_text
from app.queue import IngestionQueue
from app.retrieval import KeywordRetriever
from app.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    DocumentCreate,
    IncidentCreate,
    IncidentOut,
    ProjectCreate,
    ProjectOut,
    TenantCreate,
    TenantOut,
)

logger = logging.getLogger("contextforge")


def create_app(settings: Settings | None = None, db_url: str | None = None) -> FastAPI:
    settings = settings or get_settings()
    database = Database(db_url or settings.database_url)
    embedder = DeterministicEmbedder()
    llm = DeterministicLLM()
    queue = IngestionQueue()
    retriever = KeywordRetriever()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await database.create_all()
        yield
        await database.dispose()

    app = FastAPI(title="ContextForge API", version="0.1.0", lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.state.embedder = embedder
    app.state.llm = llm
    app.state.queue = queue
    app.state.retriever = retriever

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID")
        valid_request_id = (
            supplied_request_id
            and len(supplied_request_id) <= 128
            and supplied_request_id.isprintable()
        )
        request_id = supplied_request_id if valid_request_id else secrets.token_hex(16)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_request_error", extra={"request_id": request_id})
            response = JSONResponse(
                status_code=500,
                content={"detail": "internal server error", "request_id": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request.state.request_id},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "request validation failed",
                "request_id": request.state.request_id,
            },
        )

    async def db_session(request: Request):
        async with request.app.state.database.sessions() as session:
            yield session

    async def auth(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> None:
        if settings.auth_required and not settings.api_key:
            raise HTTPException(503, "authentication is not configured")
        if settings.api_key and (
            not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key)
        ):
            raise HTTPException(401, "invalid API key")
        # TODO: replace this shared key with tenant-scoped JWT/API-key verification.

    async def get_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(404, "tenant not found")
        return tenant

    async def get_project(session: AsyncSession, project_id: UUID) -> Project:
        project = await session.get(Project, project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        return project

    @app.get("/healthz")
    async def health():
        return {"status": "ok"}

    @app.post(
        "/v1/tenants", response_model=TenantOut, status_code=201, dependencies=[Depends(auth)]
    )
    async def create_tenant(payload: TenantCreate, session: AsyncSession = Depends(db_session)):
        tenant = Tenant(name=payload.name)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return tenant

    @app.post(
        "/v1/projects", response_model=ProjectOut, status_code=201, dependencies=[Depends(auth)]
    )
    async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(db_session)):
        await get_tenant(session, payload.tenant_id)
        project = Project(tenant_id=payload.tenant_id, name=payload.name)
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project

    @app.post(
        "/v1/incidents",
        response_model=IncidentOut,
        status_code=201,
        dependencies=[Depends(auth)],
    )
    async def create_incident(
        payload: IncidentCreate, session: AsyncSession = Depends(db_session)
    ):
        await get_project(session, payload.project_id)
        incident = Incident(**payload.model_dump())
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
        return incident

    @app.post(
        "/v1/projects/{project_id}/documents",
        status_code=201,
        dependencies=[Depends(auth)],
    )
    async def ingest_document(
        project_id: UUID,
        payload: DocumentCreate,
        request: Request,
        session: AsyncSession = Depends(db_session),
    ):
        await get_project(session, project_id)
        if len(payload.content.encode()) > settings.max_document_bytes:
            raise HTTPException(413, "document exceeds configured size limit")
        content_hash = hashlib.sha256(payload.content.encode()).hexdigest()
        existing = await session.scalar(
            select(Document).where(
                Document.project_id == project_id, Document.content_hash == content_hash
            )
        )
        if existing:
            return {"id": existing.id, "status": existing.status, "duplicate": True}
        document = Document(
            project_id=project_id,
            title=payload.title,
            content=payload.content,
            content_hash=content_hash,
        )
        session.add(document)
        try:
            await session.flush()
            for chunk in chunk_text(payload.content):
                embedding = await request.app.state.embedder.embed(chunk.content)
                session.add(
                    DocumentChunk(
                        document_id=document.id,
                        ordinal=chunk.ordinal,
                        content=chunk.content,
                        embedding=json.dumps(embedding),
                    )
                )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(
                select(Document).where(
                    Document.project_id == project_id, Document.content_hash == content_hash
                )
            )
            if existing:
                return {"id": existing.id, "status": existing.status, "duplicate": True}
            raise
        await request.app.state.queue.enqueue(str(document.id))
        return {"id": document.id, "status": document.status, "duplicate": False}

    @app.post(
        "/v1/incidents/{incident_id}/ask",
        response_model=AskResponse,
        dependencies=[Depends(auth)],
    )
    async def ask_incident(
        incident_id: UUID,
        payload: AskRequest,
        request: Request,
        session: AsyncSession = Depends(db_session),
    ):
        incident = await session.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(404, "incident not found")
        documents = list(
            await session.scalars(
                select(Document).where(Document.project_id == incident.project_id)
            )
        )
        chunk_list = await request.app.state.retriever.retrieve(
            session, incident.project_id, payload.question
        )
        doc_map = {doc.id: doc for doc in documents}
        evidence = [item.content for item in chunk_list if item.content]
        answer = await request.app.state.llm.answer(payload.question, evidence)
        citations = [
            Citation(
                document_id=item.document_id,
                title=doc_map[item.document_id].title,
                chunk_id=item.id,
                excerpt=item.content[:300],
            )
            for item in chunk_list
            if item.document_id in doc_map
        ]
        confidence = min(0.95, 0.35 + 0.2 * len(citations)) if citations else 0.1
        uncertainty = (
            ["Evidence is limited; validate against live observability data."]
            if confidence < 0.75
            else []
        )
        return AskResponse(
            answer=answer, confidence=confidence, uncertainty=uncertainty, citations=citations
        )

    return app


app = create_app()
