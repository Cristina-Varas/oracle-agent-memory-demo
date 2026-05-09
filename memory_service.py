import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

import oci
import oracledb
from dotenv import load_dotenv
from langchain_oci import ChatOCIGenAI, OCIGenAIEmbeddings
from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.oracledbmemorystore import OracleDBMemoryStore

from oci_agent_memory_adapters import OCIChatLlm, OCIGenAIEmbedder


CATEGORIES = [
    "Customer Engagement",
    "Internal Notes",
    "Platform / Product",
    "Technical Issue",
    "Demo / PoC",
    "Architecture",
    "Follow-up / Next Steps",
]

DEFAULT_OCI_CONFIG_FILE = "~/.oci/config"
DEFAULT_OCI_GENAI_ENDPOINT = "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com"
DEFAULT_EMBED_MODEL_ID = "cohere.embed-english-v3.0"
DEFAULT_CHAT_MODEL_ID = "cohere.command-a-03-2025"
DEFAULT_EMBED_DIMENSIONS = 1024
DEFAULT_TABLE_PREFIX = "APP_"


class MemoryServiceError(Exception):
    pass


class ConfigurationError(MemoryServiceError):
    pass


class DatabaseInitializationError(MemoryServiceError):
    pass


class OCIConfigError(MemoryServiceError):
    pass


class EmbeddingModelError(MemoryServiceError):
    pass


class ChatModelError(MemoryServiceError):
    pass


class AgentMemoryInitializationError(MemoryServiceError):
    pass


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    title: str
    content: str
    category: str
    customer_project: str | None
    tags: list[str]
    source: str | None
    created_at: str | None


@dataclass
class MemoryClient:
    pool: Any
    memory: OracleAgentMemory
    llm: OCIChatLlm
    table_prefix: str


def get_memory_client() -> MemoryClient:
    return _get_memory_client()


def add_memory(
    title: str,
    content: str,
    category: str,
    customer_project: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
) -> str:
    _validate_category(category)
    if not title.strip():
        raise ValueError("Title is required.")
    if not content.strip():
        raise ValueError("Content is required.")

    client = get_memory_client()
    memory_id = f"mem_{uuid4().hex}"
    clean_tags = _clean_tags(tags)
    metadata = {
        "title": title.strip(),
        "content": content.strip(),
        "category": category,
        "customer_project": _empty_to_none(customer_project),
        "tags": clean_tags,
        "source": _empty_to_none(source),
        "created_at": datetime.now(UTC).isoformat(),
    }
    indexed_content = _format_memory_text(
        title=title,
        content=content,
        category=category,
        customer_project=customer_project,
        tags=clean_tags,
        source=source,
    )

    try:
        return client.memory.add_memory(
            indexed_content,
            memory_id=memory_id,
            metadata=metadata,
        )
    except Exception as exc:
        raise MemoryServiceError(f"Could not add memory: {exc}") from exc


def search_memories(
    query: str,
    category: str | None = None,
    customer_project: str | None = None,
    tags: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    if category:
        _validate_category(category)

    client = get_memory_client()
    requested = max(limit * 5, limit, 10)

    try:
        results = client.memory.search(query, user_id=None, max_results=requested)
    except Exception as exc:
        raise MemoryServiceError(f"Could not search memories: {exc}") from exc

    filtered = []
    for result in results:
        record = _search_result_to_dict(result)
        if _matches_filters(record, category, customer_project, tags):
            filtered.append(record)
        if len(filtered) >= limit:
            break
    return filtered


def list_memories(limit: int = 50) -> list[dict[str, Any]]:
    client = get_memory_client()
    table_name = f"{client.table_prefix}MEMORY"
    sql = f"""
        select
            record_id,
            content,
            json_serialize(metadata returning clob),
            created_at
        from {table_name}
        order by created_at desc
        fetch first :limit rows only
    """

    try:
        with client.pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, limit=limit)
                return [_row_to_memory_dict(row) for row in cur]
    except Exception as exc:
        raise MemoryServiceError(f"Could not list memories: {exc}") from exc


def delete_memory(memory_id: str) -> int:
    if not memory_id:
        raise ValueError("memory_id is required.")

    client = get_memory_client()
    try:
        return client.memory.delete_memory(memory_id)
    except Exception as exc:
        raise MemoryServiceError(f"Could not delete memory: {exc}") from exc


def chat_with_memory(
    question: str,
    category: str | None = None,
    customer_project: str | None = None,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Question is required.")

    sources = search_memories(
        question,
        category=category,
        customer_project=customer_project,
        limit=6,
    )
    context = _format_context(sources)
    prompt = f"""
You are a practical assistant answering from the saved Oracle Agent Memory records.
Use only the memory context below. If the answer is not present, say that the saved
memory does not contain enough information.
Write in plain text only. Do not use Markdown, bullet syntax, numbered lists,
asterisks, backticks, tables, headings, or bold formatting. Use short paragraphs.

Memory context:
{context}

Question:
{question.strip()}
""".strip()

    try:
        response = get_memory_client().llm.generate(prompt)
    except Exception as exc:
        raise MemoryServiceError(f"Could not generate chat response: {exc}") from exc

    return {
        "answer": _plain_text(response.text),
        "sources": sources,
    }


@lru_cache(maxsize=1)
def _get_memory_client() -> MemoryClient:
    load_dotenv()
    env = _load_settings()
    _validate_oci_config(env["OCI_CONFIG_FILE"])

    pool = _create_pool(env)
    embedder = _create_embedder(env)
    llm = _create_llm(env)
    memory = _create_memory_client(pool, embedder, llm, env)

    return MemoryClient(
        pool=pool,
        memory=memory,
        llm=llm,
        table_prefix=env["MEMORY_TABLE_PREFIX"],
    )


def _load_settings() -> dict[str, Any]:
    env = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "CONNECT_STRING": os.getenv("CONNECT_STRING"),
        "OCI_CONFIG_FILE": os.getenv("OCI_CONFIG_FILE", DEFAULT_OCI_CONFIG_FILE),
        "OCI_COMPARTMENT_ID": os.getenv("OCI_COMPARTMENT_ID"),
        "OCI_GENAI_ENDPOINT": os.getenv("OCI_GENAI_ENDPOINT", DEFAULT_OCI_GENAI_ENDPOINT),
        "OCI_EMBED_MODEL_ID": os.getenv("OCI_EMBED_MODEL_ID", DEFAULT_EMBED_MODEL_ID),
        "OCI_EMBED_DIMENSIONS": int(
            os.getenv("OCI_EMBED_DIMENSIONS", str(DEFAULT_EMBED_DIMENSIONS))
        ),
        "OCI_CHAT_MODEL_ID": os.getenv("OCI_CHAT_MODEL_ID", DEFAULT_CHAT_MODEL_ID),
        "MEMORY_TABLE_PREFIX": os.getenv("MEMORY_TABLE_PREFIX", DEFAULT_TABLE_PREFIX),
    }
    missing = [key for key, value in env.items() if key != "MEMORY_TABLE_PREFIX" and not value]
    if missing:
        raise ConfigurationError(f"Missing required .env values: {', '.join(missing)}")

    connect_string = env["CONNECT_STRING"]
    is_descriptor = connect_string.strip().lower().startswith("(description=")
    is_easy_connect = "/" in connect_string or ":" in connect_string
    if not is_descriptor and not is_easy_connect:
        raise ConfigurationError(
            "CONNECT_STRING looks like a wallet alias. Use the full TLS connection string."
        )
    return env


def _validate_oci_config(config_file: str) -> None:
    path = Path(config_file).expanduser()
    if not path.exists():
        raise OCIConfigError(f"OCI config file not found: {path}")

    try:
        config = oci.config.from_file(str(path), "DEFAULT")
        oci.config.validate_config(config)
    except Exception as exc:
        raise OCIConfigError(f"OCI config could not be loaded: {exc}") from exc

    key_file = Path(config["key_file"]).expanduser()
    if not key_file.exists():
        raise OCIConfigError(f"OCI key_file does not exist: {key_file}")


def _create_pool(env: dict[str, Any]) -> Any:
    try:
        return oracledb.create_pool(
            user=env["DB_USER"],
            password=env["DB_PASSWORD"],
            dsn=env["CONNECT_STRING"],
            min=1,
            max=4,
            increment=1,
        )
    except Exception as exc:
        raise DatabaseInitializationError(f"Database pool could not be created: {exc}") from exc


def _create_embedder(env: dict[str, Any]) -> OCIGenAIEmbedder:
    try:
        embeddings = OCIGenAIEmbeddings(
            auth_type="API_KEY",
            auth_file_location=env["OCI_CONFIG_FILE"],
            auth_profile="DEFAULT",
            service_endpoint=env["OCI_GENAI_ENDPOINT"],
            compartment_id=env["OCI_COMPARTMENT_ID"],
            model_id=env["OCI_EMBED_MODEL_ID"],
            input_type="SEARCH_DOCUMENT",
        )
        embeddings.embed_query("health check")
        return OCIGenAIEmbedder(embeddings)
    except Exception as exc:
        raise EmbeddingModelError(f"Embedding model could not be initialized: {exc}") from exc


def _create_llm(env: dict[str, Any]) -> OCIChatLlm:
    try:
        chat = ChatOCIGenAI(
            auth_type="API_KEY",
            auth_file_location=env["OCI_CONFIG_FILE"],
            auth_profile="DEFAULT",
            service_endpoint=env["OCI_GENAI_ENDPOINT"],
            compartment_id=env["OCI_COMPARTMENT_ID"],
            model_id=env["OCI_CHAT_MODEL_ID"],
            provider="cohere",
            model_kwargs={"temperature": 0, "max_tokens": 512},
        )
        llm = OCIChatLlm(chat)
        llm.generate("Reply with exactly: OK")
        return llm
    except Exception as exc:
        raise ChatModelError(f"Chat model could not be initialized: {exc}") from exc


def _create_memory_client(
    pool: Any,
    embedder: OCIGenAIEmbedder,
    llm: OCIChatLlm,
    env: dict[str, Any],
) -> OracleAgentMemory:
    try:
        store = OracleDBMemoryStore(
            embedder=embedder,
            pool=pool,
            schema_policy="create_if_necessary",
            vector_dim=env["OCI_EMBED_DIMENSIONS"],
            table_name_prefix=env["MEMORY_TABLE_PREFIX"],
        )
        return OracleAgentMemory(
            store=store,
            llm=llm,
            extract_memories=False,
        )
    except Exception as exc:
        raise AgentMemoryInitializationError(
            f"OracleAgentMemory could not be initialized: {exc}"
        ) from exc


def _format_memory_text(
    title: str,
    content: str,
    category: str,
    customer_project: str | None,
    tags: list[str],
    source: str | None,
) -> str:
    parts = [
        f"Title: {title.strip()}",
        f"Category: {category}",
    ]
    if customer_project:
        parts.append(f"Customer / Project: {customer_project.strip()}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    if source:
        parts.append(f"Source: {source.strip()}")
    parts.append("")
    parts.append(content.strip())
    return "\n".join(parts)


def _format_context(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No matching memories were found."

    lines = []
    for index, record in enumerate(records, 1):
        lines.append(
            "\n".join(
                [
                    f"[{index}] {record['title']}",
                    f"Category: {record['category']}",
                    f"Project: {record.get('customer_project') or 'N/A'}",
                    f"Tags: {', '.join(record.get('tags') or []) or 'N/A'}",
                    f"Content: {record['content']}",
                ]
            )
        )
    return "\n\n".join(lines)


def _search_result_to_dict(result: Any) -> dict[str, Any]:
    record = getattr(result, "record", None)
    metadata = _metadata_to_dict(getattr(record, "metadata", None))
    content = getattr(result, "content", None) or getattr(record, "content", "")
    memory_id = getattr(record, "record_id", None) or getattr(record, "id", "")
    created_at = getattr(record, "created_at", None)
    return _memory_dict(memory_id, content, metadata, created_at, score=getattr(result, "score", None))


def _row_to_memory_dict(row: Any) -> dict[str, Any]:
    memory_id, content, metadata_json, created_at = row
    metadata = _metadata_to_dict(_lob_to_text(metadata_json))
    return _memory_dict(memory_id, _lob_to_text(content), metadata, created_at)


def _memory_dict(
    memory_id: str,
    content: str,
    metadata: dict[str, Any],
    created_at: Any,
    score: float | None = None,
) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "title": metadata.get("title") or _first_line(content),
        "content": metadata.get("content") or content,
        "category": metadata.get("category") or "Internal Notes",
        "customer_project": metadata.get("customer_project"),
        "tags": metadata.get("tags") or [],
        "source": metadata.get("source"),
        "created_at": metadata.get("created_at") or _stringify_datetime(created_at),
        "score": score,
    }


def _metadata_to_dict(metadata: Any) -> dict[str, Any]:
    if not metadata:
        return {}
    if isinstance(metadata, dict):
        return metadata
    text = _lob_to_text(metadata)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _matches_filters(
    record: dict[str, Any],
    category: str | None,
    customer_project: str | None,
    tags: list[str] | None,
) -> bool:
    if category and record.get("category") != category:
        return False
    if customer_project:
        project = record.get("customer_project") or ""
        if customer_project.lower().strip() not in project.lower():
            return False
    clean_tags = set(_clean_tags(tags))
    record_tags = {tag.lower() for tag in record.get("tags") or []}
    return not clean_tags or clean_tags.issubset(record_tags)


def _validate_category(category: str) -> None:
    if category not in CATEGORIES:
        raise ValueError(f"Unsupported category: {category}")


def _clean_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    cleaned = []
    for tag in tags:
        value = tag.strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _empty_to_none(value: str | None) -> str | None:
    if value and value.strip():
        return value.strip()
    return None


def _first_line(value: str) -> str:
    return value.strip().splitlines()[0][:80] if value else "Untitled"


def _stringify_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _lob_to_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "read"):
        return value.read()
    return str(value)


def _plain_text(value: str) -> str:
    replacements = (
        ("**", ""),
        ("__", ""),
        ("`", ""),
    )
    text = value
    for old, new in replacements:
        text = text.replace(old, new)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            stripped = stripped[2:].strip()
        if len(stripped) > 3 and stripped[0].isdigit() and ". " in stripped[:4]:
            stripped = stripped.split(". ", 1)[1].strip()
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        lines.append(stripped)
    return "\n".join(lines).strip()
