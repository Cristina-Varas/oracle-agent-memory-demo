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
AGENT_MEMORY_API_KEY=
```

The application uses `APP_` tables by default. The existing smoke tests keep their own demo prefixes.

`AGENT_MEMORY_API_KEY` enables simple API key protection for FastAPI. When it is empty, requests are allowed for local development and the API prints a startup warning. When it has a value, every API request must include:

```text
X-API-Key: your-key
```

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

For Oracle APEX or another machine on your network, bind to all interfaces:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
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

If `AGENT_MEMORY_API_KEY` is enabled in the backend, pass the same key to the frontend:

```bash
VITE_AGENT_MEMORY_API_KEY=your-key npm run dev
```

## Refresh Ngrok For APEX

When APEX runs in Autonomous Database, it cannot call `localhost:8000`. Use ngrok to expose the local FastAPI backend through a temporary public URL.

The helper script starts FastAPI if needed, starts or reuses an ngrok tunnel, tests `/health`, and prints the APEX initialization block:

```bash
scripts/refresh_ngrok.sh
```

Use the printed values in your APEX application initialization process:

```plsql
begin
    :G_AGENT_MEMORY_API_URL := 'https://your-current-ngrok-url.ngrok-free.app';
    :G_AGENT_MEMORY_API_KEY := 'your-key';
end;
```

Free ngrok URLs can change whenever the tunnel is restarted. To avoid updating APEX every time, use a reserved/static ngrok domain or deploy the FastAPI backend to a stable public service.

## Run The Streamlit Demo

```bash
streamlit run app.py
```

Both UIs support:

- Add Memory
- Search Memories
- Chat with Memory
- Manage Memories
- Models

Chat is read-only. It searches existing memories and sends that context to the chat model, but it never creates or updates memory records.

## Model Management

The React application includes a **Models** page. It shows the active OCI chat model, the fixed embedding model and dimensions, selectable OCI chat model options, and a custom chat model field.

The embedding model is shown but not changed from the UI because changing embeddings can require a different vector dimension and database schema. The chat model can be changed at runtime.

Runtime chat model overrides are saved locally in:

```text
.runtime_config.json
```

This file is ignored by Git.

Get the active model configuration:

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/models
```

Set the active chat model:

```bash
curl -X POST http://localhost:8000/models/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "model_id": "cohere.command-a-03-2025",
    "provider": "cohere",
    "validate": true
  }'
```

When `validate` is `true`, the backend makes a short OCI Generative AI call before saving the model.

## FastAPI Endpoints

Interactive docs:

```text
http://localhost:8000/docs
```

Core endpoints:

```text
GET    /health
POST   /memories
GET    /memories
POST   /search
POST   /chat
DELETE /memories/{memory_id}
GET    /models
POST   /models/chat
```

All error responses use this JSON shape:

```json
{
  "error": "Bad request",
  "detail": "Unsupported category: Example"
}
```

### Test Health

Without API key in local development:

```bash
curl http://localhost:8000/health
```

With API key enabled:

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/health
```

### Create Memory

```bash
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "title": "Customer follow-up",
    "content": "Customer asked for a follow-up session on AI Vector Search and Agent Memory.",
    "category": "Follow-up / Next Steps",
    "customer_project": "Example Customer",
    "tags": ["follow-up", "vector-search"],
    "source": "meeting"
  }'
```

Response:

```json
{
  "memory_id": "mem_example",
  "status": "created"
}
```

### Search Memories

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "query": "AI Vector Search follow-up",
    "category": "Follow-up / Next Steps",
    "customer_project": "Example Customer",
    "tags": ["follow-up"],
    "limit": 10
  }'
```

Response:

```json
{
  "count": 1,
  "memories": [
    {
      "memory_id": "mem_example",
      "title": "Customer follow-up",
      "content": "Customer asked for a follow-up session on AI Vector Search and Agent Memory.",
      "category": "Follow-up / Next Steps",
      "customer_project": "Example Customer",
      "tags": ["follow-up", "vector-search"],
      "source": "meeting",
      "created_at": "2026-05-08T11:00:00+00:00",
      "score": null
    }
  ]
}
```

### Chat With Memory

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "question": "What follow-up did the customer ask for?",
    "category": "Follow-up / Next Steps",
    "customer_project": "Example Customer"
  }'
```

Response:

```json
{
  "answer": "The customer asked for a follow-up session on AI Vector Search and Agent Memory.",
  "used_memories": [
    {
      "title": "Customer follow-up",
      "category": "Follow-up / Next Steps",
      "customer_project": "Example Customer",
      "source": "meeting",
      "score": null,
      "content_preview": "Customer asked for a follow-up session on AI Vector Search and Agent Memory."
    }
  ]
}
```

## Oracle APEX Consumption

Use APEX **Shared Components > Web Source Modules** or `APEX_WEB_SERVICE` to call the FastAPI service.

Recommended APEX setup:

- Base URL: `http://your-api-host:8000`
- Authentication: HTTP Header
- Header name: `X-API-Key`
- Header value: the same value as `AGENT_MEMORY_API_KEY`
- Content type for POST requests: `application/json`

APEX Web Source operations:

- Health check: `GET /health`
- Create memory: `POST /memories`
- Search report source: `POST /search`, parse `memories`
- Chat process: `POST /chat`, parse `answer` and `used_memories`
- Delete action: `DELETE /memories/{memory_id}`

For APEX reports, point the row selector to:

```text
memories
```

For chat source details, point the row selector to:

```text
used_memories
```
