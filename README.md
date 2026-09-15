\# AI Coding Agent



\## Summary



Built the foundation of an AI coding assistant that answers questions about a codebase using real semantic search — not keyword matching. The system parses Python files into functions/classes using Tree-sitter, embeds each piece with Gemini's embedding model, stores them in PostgreSQL with pgvector, and retrieves the most relevant code for any question before asking Gemini to answer using that context. Every request — tokens, latency, cost, success/failure — gets logged to the database for later cost analysis.



Along the way: fought through a Windows PATH corruption issue, reset a forgotten Postgres password, and switched pgvector from a native Windows install to the official Docker image after Visual Studio Build Tools weren't available.



\*\*Status:\*\* Phase 1 (Foundation) fully complete — indexing, embedding, retrieval, and the `/chat` API all working end-to-end and tested with real questions against the app's own source code.



\---



\## Results Achieved



\*\*Retrieval quality (semantic search via pgvector):\*\*

\- Questions directly about the codebase returned highly relevant chunks, similarity scores ranging \*\*0.55–0.68\*\*

&#x20; - "How does the LLM client work?" → top match: `get\_llm\_client` (0.682)

&#x20; - "What tables exist and what do they store?" → top match: `init\_db` (0.620)

&#x20; - "How does the code get split into chunks?" → top match: `\_walk` (0.654)

\- An intentionally off-topic question ("What is the weather today?") correctly scored lower (\*\*0.50–0.53\*\*), and the model correctly responded that it had no relevant information — no hallucination.



\*\*End-to-end pipeline correctness:\*\*

\- 28 code chunks successfully extracted from the app's own source (`app/`) via Tree-sitter AST parsing

\- All 28 chunks embedded (3072-dim vectors via `gemini-embedding-001`) and stored in Postgres/pgvector

\- 4 live `/chat` requests tested via curl, all logged correctly to `request\_logs` with accurate token counts and status



\*\*Baseline performance numbers (4 requests):\*\*



| Metric | Value |

|---|---|

| Average latency | \~9.4 seconds |

| Average input tokens/request | \~810 |

| Total output tokens (4 requests) | 1,377 |



These numbers are the baseline to compare against once Phase 3 (compression) and Phase 4 (caching) are built — the whole point of those phases is bringing latency and token cost down from this starting point.



\---



\## Phase 1 — Foundation, Step by Step



\### 1.1 Project structure, FastAPI skeleton ✅

\- `app/api`, `app/core`, `app/models`, `app/services` — each with `\_\_init\_\_.py`

\- `main.py` at project root running the FastAPI app



\### 1.2 PostgreSQL + pgvector installed and running ✅

\- Native PostgreSQL 16 installed on Windows initially (kept, but unused going forward)

\- pgvector added via the \*\*official Docker image\*\* `pgvector/pgvector:pg16` instead of compiling from source or using third-party Windows binaries

\- Container name: `pgvector-db`, mapped to port `5433` (native Postgres still owns `5432`)

\- Container set to auto-restart: `docker update --restart unless-stopped pgvector-db`

\- Database created: `ai\_coding\_agent`

\- Extension enabled: `CREATE EXTENSION vector;` — confirmed version `0.8.6`



\### 1.3 DB models: `request\_logs`, `cache\_entries`, `code\_chunks` ✅

\- `app/core/database.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get\_db()`

\- `app/models/request\_log.py` — logs every request: question, tokens, cost, latency, cache\_hit, status

\- `app/models/cache\_entry.py` — exact-match cache: query\_hash, query\_text, response\_text, hit\_count

\- `app/models/code\_chunk.py` — indexed code pieces with `embedding` column (`Vector(3072)`)

\- Tables created via `app/core/init\_db.py`, run with: `python -m app.core.init\_db`



\### 1.4 Swappable LLM client ✅

\- `app/services/llm\_client.py`

\- Abstract base class `LLMClient` with a `generate(prompt) -> dict` interface

\- `GeminiClient` — fully working, uses `google-genai` SDK

\- `ClaudeClient` / `OpenAIClient` — stubs, raise `NotImplementedError` until implemented

\- `get\_llm\_client(provider)` factory function selects the right client



\*\*Note on model names:\*\* Available Gemini models as of this session include `gemini-3.6-flash` (used for chat) and `gemini-embedding-001` (used for embeddings, outputs \*\*3072 dimensions\*\*, not the older 768 from `text-embedding-004`).



\### 1.5 Tree-sitter AST indexer (Python) ✅

\- `app/services/indexer.py`

\- Uses `tree-sitter` + `tree-sitter-python` (official PyPI packages)

\- Parses `.py` files into an AST, extracts `function\_definition` and `class\_definition` nodes as chunks

\- Descends into classes (to catch methods) but not into function bodies (avoids duplicate nested chunks)

\- `index\_directory()` walks a folder recursively, skipping `venv`, `\_\_pycache\_\_`, `.git`, `node\_modules`



\### 1.6 Embedding generation for code chunks ✅

\- `app/services/embedder.py`

\- Uses `gemini-embedding-001`, outputs 3072-dim vectors

\- `embed\_text()` — single string in, vector out

\- `embed\_chunks()` — batch version for indexer output



\### 1.7 Semantic retriever (pgvector similarity search) ✅

\- `app/services/retriever.py`

\- Embeds the incoming question, then uses pgvector's `cosine\_distance()` to rank stored code chunks

\- Returns top-k chunks with a similarity score (1 - distance)



\### 1.8 `POST /chat` endpoint ✅

\- `main.py` rewritten to tie everything together:

&#x20; 1. Retrieve relevant code chunks for the question

&#x20; 2. Build a prompt with that context injected

&#x20; 3. Call the LLM via `get\_llm\_client()`

&#x20; 4. Log the request (tokens, latency, status) to `request\_logs`

&#x20; 5. Return the answer + source chunks used + latency

\- Handles errors by still logging a failed request before re-raising



\### 1.9 End-to-end testing ✅

Tested with curl against the running server (`uvicorn main:app --reload`):

\- Questions about the codebase itself (LLM client, DB tables, chunking logic) → high similarity scores (0.55–0.68), accurate grounded answers

\- An off-topic question ("What is the weather today?") → correctly low similarity (\~0.50–0.53) and the model correctly said it had no relevant information, rather than hallucinating



\---



\## Key setup notes / gotchas hit along the way



\- \*\*PATH issues on Windows:\*\* `setx` truncates PATH at 1024 characters and can silently break other tools (lost `python` from PATH this way — fixed since venv has its own Python anyway). Prefer the GUI environment variable editor for permanent changes.

\- \*\*Multiple Postgres versions installed\*\* (16 and 17) — only 16 is actually running as a service; 17 was an unused leftover.

\- \*\*postgres user password\*\* had to be reset via temporarily setting `pg\_hba.conf` auth method to `trust`, then reverted back to `scram-sha-256` after setting a new password.

\- \*\*pgvector on native Windows Postgres\*\* was avoided — no official Windows binary exists; building from source requires Visual Studio C++ Build Tools. Switched to the official Docker image instead for a supported, unmodified install.

\- \*\*`python-dotenv` was intentionally removed\*\* — replaced with a small hand-written `.env` parser in `app/core/config.py` using only Python's built-in `os` and `pathlib`.

\- \*\*Embedding model changed:\*\* originally planned `text-embedding-004` (768-dim) is not available on this account; using `gemini-embedding-001` (3072-dim) instead. `code\_chunks.embedding` column updated to `Vector(3072)` accordingly.

\- \*\*Docker containers don't restart automatically\*\* by default after Docker Desktop restarts — fixed with `docker update --restart unless-stopped pgvector-db`.



\---



\## Environment reference



\- \*\*Database (Docker):\*\* `postgresql://postgres:devpassword@localhost:5433/ai\_coding\_agent`

\- \*\*Start container if stopped:\*\* `docker start pgvector-db`

\- \*\*Run server:\*\* `uvicorn main:app --reload` (from project root, venv active)

\- \*\*Re-index codebase:\*\* `python -m app.services.index\_pipeline`



\---



\## What's next



\*\*Phase 2 — Cost/Token Dashboard:\*\* aggregate stats endpoint, basic React dashboard, per-question cost breakdown.

## Phase 2 — Cost/Token Dashboard

### 2.1 `GET /stats` endpoint ✅
- `app/api/stats.py`
- `GET /stats` — aggregate totals: request count, total cost, total input/output tokens, average latency, cache hit rate, error count
- `GET /stats/by-question` — per-request breakdown (last 20 by default): question, model, tokens, cost, latency, status
- Wired into `main.py` via `app.include_router(stats_router)`

### 2.2 Basic React dashboard page ✅
- Scaffolded with Vite (`npm create vite@latest frontend -- --template react`), running on `http://localhost:5173`
- `frontend/src/App.jsx` — fetches `/stats` and `/stats/by-question` on load, renders stat cards + a request table
- Failed requests are visually highlighted (red row) in the table
- CORS enabled on the FastAPI backend (`CORSMiddleware`, allowing `localhost:5173`) so the frontend can call the API across ports

### 2.3 Per-question cost breakdown view ✅
- Delivered by the same `/stats/by-question` endpoint + the "Recent Requests" table in the dashboard
- Shows exact cost, tokens, latency, and status per individual question
- Note: a true per-*file* breakdown (cost attributed to which code chunks get pulled into requests) is not yet built — would need to track which source chunks were used per request more explicitly

### Real cost tracking added
- `app/services/pricing.py` — calculates real `cost_usd` per request based on Gemini's actual pricing
- Gemini 3.6 Flash: $0.75 / million input tokens, $3.75 / million output tokens (promotional rate through Dec 31, 2026, per Google Cloud's pricing page)
- Wired into `/chat` in `main.py` so every successful request now logs a real dollar cost, not a placeholder `0.0`

---

## What's next

**Phase 3 — Compression:** strip whitespace/redundancy before sending to the LLM, measure impact against this session's baseline numbers.

\*\*Phase 3 — Compression:\*\* strip whitespace/redundancy before sending to the LLM, measure impact against this session's baseline numbers.



\*\*Phase 4 — Caching:\*\* wire the already-scaffolded `cache\_entries` table into `/chat`, then add semantic (near-duplicate) cache matching.

