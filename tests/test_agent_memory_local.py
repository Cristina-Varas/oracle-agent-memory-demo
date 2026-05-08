import hashlib
import os
from uuid import uuid4

import numpy as np
import oracledb
from dotenv import load_dotenv
from oracleagentmemory.apis.searchscope import SearchScope
from oracleagentmemory.core import OracleAgentMemory


class LocalTestEmbedder:
    """Deterministic embedder for smoke-testing the database memory layer."""

    dimensions = 384

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            repeated = (digest * ((self.dimensions // len(digest)) + 1))[: self.dimensions]
            vector = np.frombuffer(repeated, dtype=np.uint8).astype(np.float32)
            norm = np.linalg.norm(vector)
            vectors.append(vector / norm if norm else vector)
        return np.vstack(vectors)

    async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        return self.embed(texts, is_query=is_query)


load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
CONNECT_STRING = os.getenv("CONNECT_STRING")

if not all([DB_USER, DB_PASSWORD, CONNECT_STRING]):
    raise ValueError("Missing DB_USER, DB_PASSWORD or CONNECT_STRING in .env")

pool = oracledb.create_pool(
    user=DB_USER,
    password=DB_PASSWORD,
    dsn=CONNECT_STRING,
    min=1,
    max=4,
    increment=1,
)

memory = OracleAgentMemory(
    connection=pool,
    embedder=LocalTestEmbedder(),
    extract_memories=False,
    schema_policy="create_if_necessary",
    table_name_prefix="DEMO_",
)

user_id = f"demo_user_{uuid4().hex[:8]}"
content = "Cristina is testing Oracle Agent Memory over TLS without wallet."

memory.add_user(user_id, "Demo user for Oracle Agent Memory smoke test.")
memory.add_memory(content, user_id=user_id)

results = memory.search(
    "Oracle Agent Memory TLS",
    scope=SearchScope(user_id=user_id),
    max_results=3,
)

print("OracleAgentMemory local smoke test OK")
for result in results:
    print(f"- [{result.record.record_type}] {result.content}")
