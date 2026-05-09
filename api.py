import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from memory_service import (
    CATEGORIES,
    MemoryServiceError,
    add_memory,
    chat_with_memory,
    delete_memory,
    get_model_config,
    get_memory_client,
    list_memories,
    search_memories,
    set_chat_model,
)


load_dotenv()

API_KEY = os.getenv("AGENT_MEMORY_API_KEY", "").strip()
if not API_KEY:
    print(
        "WARNING: AGENT_MEMORY_API_KEY is empty. "
        "API requests are allowed without X-API-Key for local development."
    )

app = FastAPI(
    title="Oracle Agent Memory API",
    version="1.1.0",
    description=(
        "FastAPI service for Oracle APEX and web clients to create, search, chat with, "
        "list, and delete Oracle Agent Memory records."
    ),
    contact={"name": "Oracle Agent Memory Demo"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MemoryCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Short human-readable memory title.")
    content: str = Field(..., min_length=1, description="Full memory content.")
    category: str = Field(..., description="One of the configured memory categories.")
    customer_project: str | None = Field(
        default=None,
        description="Optional customer, account, opportunity, project, or workspace name.",
    )
    tags: list[str] = Field(default_factory=list, description="Optional lowercase-friendly tags.")
    source: str | None = Field(default=None, description="Optional source such as meeting, email, demo, or call.")


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query.")
    category: str | None = Field(default=None, description="Optional exact category filter.")
    customer_project: str | None = Field(default=None, description="Optional project substring filter.")
    tags: list[str] = Field(default_factory=list, description="Optional tags that must all match.")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results.")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to answer from saved memories.")
    category: str | None = Field(default=None, description="Optional exact category filter.")
    customer_project: str | None = Field(default=None, description="Optional project substring filter.")


class MemoryResponse(BaseModel):
    memory_id: str
    title: str
    content: str
    category: str
    customer_project: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    created_at: str | None = None
    score: float | None = None


class MemoryCreateResponse(BaseModel):
    memory_id: str
    status: str = "created"


class SearchResponse(BaseModel):
    count: int
    memories: list[MemoryResponse]


class UsedMemoryResponse(BaseModel):
    title: str
    category: str
    customer_project: str | None = None
    source: str | None = None
    score: float | None = None
    content_preview: str


class ChatResponse(BaseModel):
    answer: str
    used_memories: list[UsedMemoryResponse]


class DeleteResponse(BaseModel):
    memory_id: str
    deleted: int


class HealthResponse(BaseModel):
    status: str
    service: str


class CategoriesResponse(BaseModel):
    categories: list[str]


class ChatModelOption(BaseModel):
    model_id: str
    provider: str
    label: str
    description: str


class ModelConfigResponse(BaseModel):
    active_chat_model_id: str
    active_chat_provider: str
    embedding_model_id: str
    embedding_dimensions: int
    chat_model_options: list[ChatModelOption]
    runtime_config_file: str


class ModelUpdateRequest(BaseModel):
    model_id: str = Field(..., min_length=1, description="OCI Generative AI chat model ID.")
    provider: str = Field(default="cohere", min_length=1, description="Model provider for langchain-oci.")
    validate: bool = Field(default=True, description="Validate model by making a short OCI GenAI call before saving.")


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header.",
        )


api_key_dependency = Depends(verify_api_key)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": _status_error(exc.status_code),
            "detail": jsonable_encoder(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health",
    description="Lightweight health check for load balancers, APEX Web Source validation, and local testing.",
)
def health(_: None = api_key_dependency) -> HealthResponse:
    return HealthResponse(status="ok", service="Oracle Agent Memory API")


@app.get(
    "/health/deep",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API, database, OCI GenAI, and OracleAgentMemory initialization",
    description="Initializes the memory client and verifies the configured backend dependencies.",
)
def deep_health(_: None = api_key_dependency) -> HealthResponse:
    try:
        get_memory_client()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return HealthResponse(status="ok", service="Oracle Agent Memory API")


@app.get(
    "/config/categories",
    response_model=CategoriesResponse,
    tags=["Configuration"],
    summary="List allowed memory categories",
    description="Returns the fixed category list used by the UI and APEX forms.",
)
def categories(_: None = api_key_dependency) -> CategoriesResponse:
    return CategoriesResponse(categories=CATEGORIES)


@app.get(
    "/models",
    response_model=ModelConfigResponse,
    tags=["Configuration"],
    summary="Get active OCI model configuration",
    description="Returns the active chat model, fixed embedding model and selectable chat model options.",
)
def models(_: None = api_key_dependency) -> ModelConfigResponse:
    try:
        return ModelConfigResponse(**get_model_config())
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/models/chat",
    response_model=ModelConfigResponse,
    tags=["Configuration"],
    summary="Set active OCI chat model",
    description=(
        "Updates the runtime chat model used by /chat. The embedding model is intentionally fixed "
        "because changing it can require a different vector dimension and schema."
    ),
)
def update_chat_model(payload: ModelUpdateRequest, _: None = api_key_dependency) -> ModelConfigResponse:
    try:
        return ModelConfigResponse(
            **set_chat_model(
                model_id=payload.model_id,
                provider=payload.provider,
                validate=payload.validate,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/memories",
    response_model=MemoryCreateResponse,
    tags=["Memories"],
    summary="Create a memory",
    description="Creates one memory record. Chat endpoints never create or update memories.",
)
def create_memory(payload: MemoryCreateRequest, _: None = api_key_dependency) -> MemoryCreateResponse:
    try:
        memory_id = add_memory(
            title=payload.title,
            content=payload.content,
            category=payload.category,
            customer_project=payload.customer_project,
            tags=payload.tags,
            source=payload.source,
        )
        return MemoryCreateResponse(memory_id=memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    "/memories",
    response_model=SearchResponse,
    tags=["Memories"],
    summary="List recent memories",
    description="Returns recent memories ordered by creation timestamp. This is easy for APEX reports to parse.",
)
def memories(
    limit: int = Query(default=50, ge=1, le=200),
    _: None = api_key_dependency,
) -> SearchResponse:
    try:
        records = [_to_memory_response(record) for record in list_memories(limit=limit)]
        return SearchResponse(count=len(records), memories=records)
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/search",
    response_model=SearchResponse,
    tags=["Search"],
    summary="Search memories",
    description="Semantic search endpoint designed for Oracle APEX POST requests.",
)
def search(payload: MemorySearchRequest, _: None = api_key_dependency) -> SearchResponse:
    try:
        records = [
            _to_memory_response(record)
            for record in search_memories(
                query=payload.query,
                category=payload.category,
                customer_project=payload.customer_project,
                tags=payload.tags,
                limit=payload.limit,
            )
        ]
        return SearchResponse(count=len(records), memories=records)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    "/memories/search",
    response_model=list[MemoryResponse],
    tags=["Search"],
    summary="Search memories with query parameters",
    description="Compatibility endpoint for the existing React client. Prefer POST /search for APEX.",
)
def search_compat(
    query: str = Query(min_length=1),
    category: str | None = None,
    customer_project: str | None = None,
    tags: list[str] = Query(default=[]),
    limit: int = Query(default=10, ge=1, le=50),
    _: None = api_key_dependency,
) -> list[MemoryResponse]:
    try:
        return [
            _to_memory_response(record)
            for record in search_memories(
                query=query,
                category=category,
                customer_project=customer_project,
                tags=tags,
                limit=limit,
            )
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Chat with memory",
    description=(
        "Answers a question from matching saved memories. This endpoint is read-only and never creates "
        "or updates memory records."
    ),
)
def chat(payload: ChatRequest, _: None = api_key_dependency) -> ChatResponse:
    try:
        response = chat_with_memory(
            question=payload.question,
            category=payload.category,
            customer_project=payload.customer_project,
        )
        return ChatResponse(
            answer=response["answer"],
            used_memories=[_to_used_memory(record) for record in response["sources"]],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete(
    "/memories/{memory_id}",
    response_model=DeleteResponse,
    tags=["Memories"],
    summary="Delete a memory",
    description="Deletes a memory record by ID and returns the number of deleted records.",
)
def remove_memory(memory_id: str, _: None = api_key_dependency) -> DeleteResponse:
    try:
        return DeleteResponse(memory_id=memory_id, deleted=delete_memory(memory_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _to_memory_response(record: dict[str, Any]) -> MemoryResponse:
    return MemoryResponse(
        memory_id=record["memory_id"],
        title=record["title"],
        content=record["content"],
        category=record["category"],
        customer_project=record.get("customer_project"),
        tags=record.get("tags") or [],
        source=record.get("source"),
        created_at=record.get("created_at"),
        score=record.get("score"),
    )


def _to_used_memory(record: dict[str, Any]) -> UsedMemoryResponse:
    content = record.get("content") or ""
    return UsedMemoryResponse(
        title=record.get("title") or "Untitled",
        category=record.get("category") or "Internal Notes",
        customer_project=record.get("customer_project"),
        source=record.get("source"),
        score=record.get("score"),
        content_preview=_preview(content),
    )


def _preview(content: str, max_length: int = 280) -> str:
    compact = " ".join(content.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "..."


def _status_error(status_code: int) -> str:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "Unauthorized"
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "Bad request"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "Not found"
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "Service unavailable"
    return "HTTP error"
