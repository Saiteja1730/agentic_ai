# Agentic Research Assistant

> A production-grade **multi-agent AI research assistant** built with **LangGraph**, **FastAPI**, **Gemini 2.5 Flash**, and a **React + TypeScript** frontend. It intelligently routes queries, searches the web and uploaded PDFs, merges and re-ranks evidence, writes a cited markdown report, and self-critiques/retries its answer — streaming every step to the UI in real time via SSE.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Tech Stack](#tech-stack)
4. [Folder Structure](#folder-structure)
5. [Features](#features)
6. [Multi-Agent Workflow](#multi-agent-workflow)
7. [Routing Flow](#routing-flow)
8. [Installation (Local)](#installation-local)
9. [Environment Variables](#environment-variables)
10. [Docker Deployment](#docker-deployment)
11. [API Reference](#api-reference)
12. [Security](#security)
13. [Known Limitations](#known-limitations)
14. [Future Improvements](#future-improvements)
15. [License](#license)

---

## Project Overview

The Agentic Research Assistant is a fully autonomous, multi-agent AI system that answers user questions by:

- **Routing** queries intelligently (General / Web / PDF / Hybrid)
- **Searching** the web (Tavily) and user-uploaded PDF documents (Qdrant)
- **Collecting** and re-ranking evidence using Gemini
- **Writing** a structured markdown research report
- **Critiquing** and revising its own draft (up to 2 retries)
- **Streaming** every step to the UI via Server-Sent Events

---

## Architecture Diagram

```
User Query
    │
    ▼
FastAPI (/api/chat) ──SSE──► React Frontend
    │
    ▼
Smart Router (heuristic, zero LLM cost)
    │
    ├─ GENERAL_SIMPLE ──► Direct Response (Gemini)
    │
    ├─ WEB_SIMPLE ──► Web Search Agent (Tavily) ──► Evidence Collector ──► Writer
    │
    ├─ PDF_SIMPLE ──► PDF Search Agent (Qdrant + Hybrid Retrieval) ──► Evidence Collector ──► Writer
    │
    └─ COMPLEX_RESEARCH ──► Supervisor Agent
                                    │
                            ┌───────┴────────┐
                            ▼                ▼
                     Web Search Agent   PDF Search Agent
                       (Tavily)         (Qdrant / BM25 / Dense)
                            └───────┬────────┘
                                    ▼
                           Evidence Collector
                           (Dedup + Gemini Rerank)
                                    │
                                    ▼
                             Writer Agent
                                    │
                                    ▼
                             Critic Agent
                          ┌─────────┴──────────┐
                          ▼                     ▼
                    Retry (≤2x)          Final Answer (SSE)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Google Gemini 2.5 Flash (via `google-genai` SDK) |
| **Embeddings** | Google `text-embedding-004` (768-dim) |
| **Agent Orchestration** | LangGraph `StateGraph` with typed state |
| **Vector Database** | Qdrant (cosine similarity, session-scoped) |
| **Retrieval** | Hybrid: Dense (Qdrant) + BM25 + Gemini Reranker |
| **Web Search** | Tavily Search API |
| **Backend API** | FastAPI + Uvicorn + SSE Starlette |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **Observability** | LangSmith (optional tracing) |
| **Infrastructure** | Docker, Docker Compose, Nginx |

---

## Folder Structure

```
agenticai-project/
├── backend/
│   ├── app/
│   │   ├── agents/          # planner, supervisor, web_agent, pdf_agent, collector, writer, critic
│   │   ├── api/             # chat.py, upload.py, session.py, health.py, graph.py
│   │   ├── config/          # settings.py  (env-driven, Pydantic BaseSettings)
│   │   ├── graph/           # state.py, router.py, nodes.py, builder.py (LangGraph wiring)
│   │   ├── llm/             # gemini.py  (Google GenAI SDK wrapper with tool loop)
│   │   ├── rag/             # chunker, embeddings, qdrant_store, retriever, retrievers, reranker
│   │   ├── schemas/         # Pydantic v2 request/response models
│   │   ├── services/        # session_service.py  (in-memory session tracking)
│   │   ├── tools/           # registry.py, search.py, utilities.py
│   │   ├── utils/           # logger.py, retry.py
│   │   └── main.py          # FastAPI app entrypoint + CORS + middleware
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile           # Multi-stage Python 3.12 build, non-root user
├── frontend/
│   ├── src/
│   │   ├── components/      # Sidebar, ChatWindow, MessageBubble, FileUpload, SessionDocuments, SourceCard
│   │   ├── hooks/           # useChatStream.ts  (SSE over fetch/POST)
│   │   ├── services/        # api.ts
│   │   └── App.tsx
│   ├── nginx.conf           # Reverse proxy for /api/ with SSE headers
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile           # Node 20 build → Nginx 1.27 serve
├── docker-compose.yml
└── README.md
```

---

## Features

- ✅ **Smart Query Routing** — heuristic classifier, zero LLM quota cost per request
- ✅ **General Knowledge** — direct Gemini answers for factual/conceptual questions
- ✅ **Web Research** — Tavily search with per-snippet Gemini summarization
- ✅ **PDF Research** — upload any PDF, chunked + embedded, hybrid retrieval (Dense + BM25 + RRF)
- ✅ **Hybrid Research** — parallel web + PDF search, structured comparison report
- ✅ **PDF Fallback** — if PDF is empty, routes to General automatically
- ✅ **Partial Failure Resilience** — web fails → answers from PDF; PDF fails → answers from web
- ✅ **Gemini Reranker** — LLM-based relevance scoring of retrieved evidence
- ✅ **Critic-Writer Loop** — self-review with 5-dimension evaluation, up to 2 rewrites
- ✅ **Tool Calling** — Supervisor can use web_search, pdf_search, calculator, current_date
- ✅ **Session Management** — isolated Qdrant namespacing per session
- ✅ **Document Management** — upload, delete individual files, clear session
- ✅ **Real-Time Streaming** — SSE streams every agent step to the UI
- ✅ **Route Badges** — UI labels each answer (🧠 General / 🌐 Web / 📄 PDF / 🔀 Hybrid)
- ✅ **Error Masking** — no stack traces or API errors exposed to the client
- ✅ **LangSmith Tracing** — optional deep tracing of all LLM/tool calls

---

## Multi-Agent Workflow

### Agents

| Agent | Responsibility |
|---|---|
| **Supervisor** | Inspects state, decides next step, can call tools |
| **Planner** | Breaks question into sub-questions and search queries |
| **Web Search Agent** | Runs Tavily queries in parallel, summarizes snippets |
| **PDF Search Agent** | Hybrid retrieval (Dense + BM25 + RRF) from Qdrant |
| **Evidence Collector** | Deduplicates, Gemini-reranks, builds context string |
| **Writer Agent** | Produces structured markdown report from evidence |
| **Critic Agent** | Evaluates draft on 5 dimensions, score 0–100 |
| **Direct Response** | Bypasses research pipeline for simple queries |

### Critic Evaluation Dimensions

1. Hallucinations — claims not in evidence
2. Missing citations — unbacked assertions
3. Coverage — completeness of answer
4. Grounding — direct evidence linkage
5. Reasoning quality — logical soundness

Score ≥ 80 → approved as final answer. Score < 80 → writer retries (max 2 times).

---

## Routing Flow

```
Query + use_pdf_context flag
          │
          ▼
   ┌─────────────────────────────────────────────┐
   │  Heuristic Router (no LLM call)             │
   │                                             │
   │  compare/vs + (pdf/web) → COMPLEX_RESEARCH  │
   │  document/resume/page/summarize → PDF_SIMPLE│
   │  latest/news/current/today → WEB_SIMPLE     │
   │  what is/explain/how → GENERAL_SIMPLE       │
   │  use_pdf_context active → PDF_SIMPLE        │
   │  fallback → GENERAL_SIMPLE                  │
   └─────────────────────────────────────────────┘
          │
          ▼
   LangGraph conditional entry point
```

**PDF empty → General Fallback:**
If PDF search returns 0 chunks and the query is not explicitly document-focused, the route automatically switches to `GENERAL_SIMPLE` for a direct Gemini answer.

---

## Installation (Local)

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for Qdrant)
- Google Gemini API key
- Tavily API key

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in GOOGLE_API_KEY and TAVILY_API_KEY

# Start Qdrant locally
docker run -d -p 6333:6333 qdrant/qdrant:v1.12.4

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# .env: VITE_API_BASE_URL=http://localhost:8000/api
npm run dev
```

Visit `http://localhost:5173`

---

## Environment Variables

Copy `backend/.env.example` → `backend/.env` and fill in your values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | ✅ | — | Google GenAI API key (Gemini + Embeddings) |
| `GEMINI_MODEL` | ✅ | `gemini-2.5-flash` | Gemini model name |
| `TAVILY_API_KEY` | ✅ | — | Tavily Search API key |
| `QDRANT_URL` | ✅ | `http://qdrant:6333` | Qdrant server URL |
| `QDRANT_API_KEY` | — | `""` | Qdrant Cloud API key (optional) |
| `QDRANT_COLLECTION` | — | `research_documents` | Qdrant collection name |
| `EMBEDDING_MODEL` | — | `text-embedding-004` | Google embedding model |
| `EMBEDDING_DIM` | — | `768` | Embedding vector dimension |
| `CHUNK_SIZE` | — | `800` | PDF chunk size in characters |
| `CHUNK_OVERLAP` | — | `120` | Chunk overlap in characters |
| `TOP_K` | — | `5` | Top chunks to retrieve |
| `RETRIEVAL_THRESHOLD` | — | `0.35` | Minimum cosine similarity score |
| `MAX_UPLOAD_MB` | — | `25` | Maximum PDF upload size |
| `MAX_CRITIC_RETRIES` | — | `2` | Writer retry limit |
| `CORS_ORIGINS` | — | `http://localhost:5173,...` | Allowed CORS origins (comma-separated) |
| `APP_ENV` | — | `production` | Environment (`development`/`production`) |
| `LOG_LEVEL` | — | `INFO` | Logging level |
| `LANGSMITH_TRACING` | — | `false` | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | — | `""` | LangSmith API key |
| `LANGSMITH_PROJECT` | — | `AgenticResearchAssistant` | LangSmith project name |

**Frontend:** Copy `frontend/.env.example` → `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8000/api
```

In Docker, the frontend proxies `/api/` through Nginx — no frontend env variable needed.

### Optional: LangSmith Tracing

Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY=your_key` to enable deep execution traces of all LangGraph nodes, LLM calls, and tool invocations at [smith.langchain.com](https://smith.langchain.com/).

---

## Docker Deployment

```bash
# 1. Copy and fill in environment file
cp backend/.env.example backend/.env
# Edit backend/.env — set GOOGLE_API_KEY and TAVILY_API_KEY

# 2. Build and start all services
docker-compose up --build

# Services:
#   qdrant    → http://localhost:6333
#   backend   → http://localhost:8000  (FastAPI docs at /docs)
#   frontend  → http://localhost:5173
```

The frontend Nginx container proxies all `/api/` requests to the backend container with full SSE support (`proxy_buffering off`, `X-Accel-Buffering: no`).

### Health Check

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","app_name":"Agentic Research Assistant","environment":"production","qdrant_connected":true}
```

---

## API Reference

### `POST /api/chat`

Runs the multi-agent research graph and streams progress via Server-Sent Events.

**Request:**
```json
{
  "question": "What are the latest advances in solid-state batteries?",
  "session_id": null,
  "use_pdf_context": true
}
```

**SSE Events:**
| Event | Payload |
|---|---|
| `status` | `{ "stage": "web_search", "message": "🌐 Searching the web" }` |
| `result` | `{ "session_id", "final_answer", "sources", "retry_count", "metrics" }` |
| `error` | `{ "status": "error", "message": "friendly error message" }` |

### `POST /api/upload`

Upload a PDF for document research. Returns `{ filename, chunks_indexed, session_id }`.

### `GET /api/session/{session_id}/files`

List all uploaded files in a session.

### `DELETE /api/session/{session_id}/files/{filename}`

Remove a specific document from the session (deletes its Qdrant vectors).

### `DELETE /api/session/{session_id}`

Clear all documents from the session (deletes all session vectors from Qdrant).

### `GET /api/health`

Returns app status and Qdrant connectivity.

### `GET /api/graph`

Returns the LangGraph topology (nodes, edges, Mermaid diagram string).

---

## Security

- **No API keys exposed** — all secrets via `.env`, never committed
- **`.gitignore`** — `.env` files excluded
- **Error masking** — Gemini/Qdrant/Tavily errors are logged server-side only; clients receive generic friendly messages
- **Input validation** — Pydantic v2 validates all requests; file upload restricted to PDF ≤ 25 MB
- **Non-root Docker user** — backend container runs as `appuser`
- **Session isolation** — Qdrant filter-scoped queries guarantee cross-session data isolation
- **No collection drops** — delete operations only remove session-tagged vectors, never the collection

---

## Known Limitations

- **Session persistence** — sessions are in-memory only; restarting the backend resets session state (Qdrant vectors persist)
- **Concurrent sessions** — no per-session request queuing; high concurrency may hit Gemini rate limits
- **PDF OCR** — scanned/image PDFs without text layer will index 0 chunks (PyPDF text extraction only)
- **LangGraph memory** — uses `MemorySaver` (in-process); not suitable for multi-process/multi-replica deployments without a persistent checkpointer

---

## Future Improvements

- [ ] Persistent session store (Redis/PostgreSQL)
- [ ] Multi-replica Qdrant / LangGraph checkpointer
- [ ] PDF OCR support (Tesseract / Google Vision)
- [ ] User authentication and session history
- [ ] Streaming token-by-token (currently streams agent steps, not tokens)
- [ ] Additional tool integrations (arXiv, Wikipedia, code interpreter)
- [ ] Mobile-responsive sidebar

---

## License

MIT
