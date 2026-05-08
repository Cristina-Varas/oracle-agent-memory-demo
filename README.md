# Oracle Agent Memory Demo

Application for saving, searching, chatting with, and managing Oracle Agent Memory records backed by Autonomous Database and OCI Generative AI.

## Project Layout

```text
.
├── app.py
├── api.py
├── frontend/
│   ├── package.json
│   └── src/
├── memory_service.py
├── oci_agent_memory_adapters.py
├── requirements.txt
└── tests/
    ├── test_agent_memory_oci.py
    ├── test_agent_memory_local.py
    ├── test_db_connection.py
    ├── test_oci_config.py
    └── test_oci_genai.py
```

## Configuration

The app reads `.env` from the project root.

Required values:

```env
DB_USER=ADMIN
DB_PASSWORD=...
CONNECT_STRING=(description=...)

OCI_CONFIG_FILE=/path/to/oci/config
OCI_COMPARTMENT_ID=...
OCI_GENAI_ENDPOINT=https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com
OCI_EMBED_MODEL_ID=cohere.embed-english-v3.0
OCI_EMBED_DIMENSIONS=1024
OCI_CHAT_MODEL_ID=cohere.command-a-03-2025
```

Optional:

```env
MEMORY_TABLE_PREFIX=APP_
```

The application uses `APP_` tables by default. The existing smoke tests keep their own demo prefixes.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Verify

Run the full Oracle Agent Memory smoke test:

```bash
python tests/test_agent_memory_oci.py
```

Useful individual checks:

```bash
python tests/test_db_connection.py
python tests/test_oci_config.py
python tests/test_oci_genai.py
```

## Run The Professional App

Start the FastAPI backend:

```bash
uvicorn api:app --host localhost --port 8000
```

In another terminal, start the React frontend:

```bash
cd frontend
npm install --cache .npm-cache
npm run dev
```

Open:

```text
http://localhost:5173
```

The React app calls the API at `http://localhost:8000` by default. To point it somewhere else:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

## Run The Streamlit Demo

```bash
streamlit run app.py
```

Both UIs support:

- Add Memory
- Search Memories
- Chat with Memory
- Manage Memories

Chat is read-only. It searches existing memories and sends that context to the chat model, but it never creates or updates memory records.
