import os

from dotenv import load_dotenv
from langchain_oci import ChatOCIGenAI, OCIGenAIEmbeddings


load_dotenv()

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
OCI_CHAT_MODEL_ID = os.getenv("OCI_CHAT_MODEL_ID", "cohere.command-a-03-2025")

if not OCI_COMPARTMENT_ID:
    raise ValueError("Missing OCI_COMPARTMENT_ID in .env")

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
    model_kwargs={"temperature": 0, "max_tokens": 64},
)

vector = embeddings.embed_query("Oracle Agent Memory smoke test")
response = chat.invoke("Reply with exactly: OCI GenAI OK")

print("OCI GenAI embeddings OK")
print(f"embedding_dimensions={len(vector)}")
print("OCI GenAI chat OK")
print(response.content)
