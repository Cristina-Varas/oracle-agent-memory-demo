from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from memory_service import (
    CATEGORIES,
    MemoryServiceError,
    add_memory,
    chat_with_memory,
    delete_memory,
    get_memory_client,
    list_memories,
    search_memories,
)


app = FastAPI(title="Oracle Agent Memory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MemoryCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    category: str
    customer_project: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str | None = None


class MemoryCreateResponse(BaseModel):
    memory_id: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    category: str | None = None
    customer_project: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]


class DeleteResponse(BaseModel):
    deleted: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/deep")
def deep_health() -> dict[str, str]:
    try:
        get_memory_client()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/config/categories")
def categories() -> dict[str, list[str]]:
    return {"categories": CATEGORIES}


@app.post("/memories", response_model=MemoryCreateResponse)
def create_memory(payload: MemoryCreateRequest) -> MemoryCreateResponse:
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


@app.get("/memories")
def memories(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    try:
        return list_memories(limit=limit)
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/memories/search")
def search(
    query: str = Query(min_length=1),
    category: str | None = None,
    customer_project: str | None = None,
    tags: list[str] = Query(default=[]),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, Any]]:
    try:
        return search_memories(
            query=query,
            category=category,
            customer_project=customer_project,
            tags=tags,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete("/memories/{memory_id}", response_model=DeleteResponse)
def remove_memory(memory_id: str) -> DeleteResponse:
    try:
        return DeleteResponse(deleted=delete_memory(memory_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        response = chat_with_memory(
            question=payload.question,
            category=payload.category,
            customer_project=payload.customer_project,
        )
        return ChatResponse(**response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MemoryServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
