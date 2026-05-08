import os
import sys
from pathlib import Path
from uuid import uuid4

import oracledb
from dotenv import load_dotenv
from langchain_oci import ChatOCIGenAI, OCIGenAIEmbeddings
from oracleagentmemory.apis.searchscope import SearchScope
from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.oracledbmemorystore import OracleDBMemoryStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oci_agent_memory_adapters import OCIChatLlm, OCIGenAIEmbedder


load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
CONNECT_STRING = os.getenv("CONNECT_STRING")

OCI_CONFIG_FILE = os.getenv(
    "OCI_CONFIG_FILE",
    "~/.oci/config",
)
OCI_COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID")
OCI_GENAI_ENDPOINT = os.getenv(
    "OCI_GENAI_ENDPOINT",
    "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com",
)
OCI_EMBED_MODEL_ID = os.getenv("OCI_EMBED_MODEL_ID", "cohere.embed-english-v3.0")
OCI_EMBED_DIMENSIONS = int(os.getenv("OCI_EMBED_DIMENSIONS", "1024"))
OCI_CHAT_MODEL_ID = os.getenv("OCI_CHAT_MODEL_ID", "cohere.command-a-03-2025")

missing = [
    key
    for key, value in {
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "CONNECT_STRING": CONNECT_STRING,
        "OCI_COMPARTMENT_ID": OCI_COMPARTMENT_ID,
    }.items()
    if not value
]
if missing:
    raise ValueError(f"Missing required .env values: {', '.join(missing)}")

pool = oracledb.create_pool(
    user=DB_USER,
    password=DB_PASSWORD,
    dsn=CONNECT_STRING,
    min=1,
    max=4,
    increment=1,
)

embeddings = OCIGenAIEmbeddings(
    auth_type="API_KEY",
    auth_file_location=OCI_CONFIG_FILE,
    auth_profile="DEFAULT",
    service_endpoint=OCI_GENAI_ENDPOINT,
    compartment_id=OCI_COMPARTMENT_ID,
    model_id=OCI_EMBED_MODEL_ID,
    input_type="SEARCH_DOCUMENT",
)
chat = ChatOCIGenAI(
    auth_type="API_KEY",
    auth_file_location=OCI_CONFIG_FILE,
    auth_profile="DEFAULT",
    service_endpoint=OCI_GENAI_ENDPOINT,
    compartment_id=OCI_COMPARTMENT_ID,
    model_id=OCI_CHAT_MODEL_ID,
    provider="cohere",
    model_kwargs={"temperature": 0, "max_tokens": 256},
)

embedder = OCIGenAIEmbedder(embeddings)
store = OracleDBMemoryStore(
    embedder=embedder,
    pool=pool,
    schema_policy="create_if_necessary",
    vector_dim=OCI_EMBED_DIMENSIONS,
    table_name_prefix="OCI_DEMO_",
)

memory = OracleAgentMemory(
    store=store,
    llm=OCIChatLlm(chat),
    extract_memories=False,
)

user_id = f"oci_demo_user_{uuid4().hex[:8]}"
memory.add_user(user_id, "Demo user for Oracle Agent Memory with OCI Generative AI.")
memory.add_memory(
    "Cristina connected Oracle Agent Memory to Autonomous Database with TLS.",
    user_id=user_id,
)

results = memory.search(
    "How did Cristina connect to the database?",
    scope=SearchScope(user_id=user_id),
    max_results=3,
)

print("OracleAgentMemory OCI smoke test OK")
for result in results:
    print(f"- [{result.record.record_type}] {result.content}")
