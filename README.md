\# AI Coding Agent



\## Summary



Built a working AI coding assistant that answers questions about a codebase using real semantic search, not keyword matching. The system parses Python files into functions/classes using Tree-sitter, embeds each piece with Gemini's embedding model, stores them in PostgreSQL with pgvector, and retrieves the most relevant code for any question before asking Gemini to answer using that context. Every request is logged for cost analysis, with caching, compression, and model routing to keep costs down. The app is deployed live on Render.



\*\*Status:\*\* All 9 core phases complete. Fully deployed, fully tested end to end.



\*\*Live URL:\*\* https://ai-coding-agent-7kbo.onrender.com



\---



\## Example: How It Actually Works



Here's a real request/response cycle, showing exactly what happens end to end.



\*\*You send:\*\*



curl -X POST https://ai-coding-agent-7kbo.onrender.com/chat

\-H "Content-Type: application/json"

\-H "X-API-Key: your-api-key"

\-d '{"question": "How does the semantic cache work?"}'





\*\*What happens internally, step by step:\*\*



1\. \*\*Cache check\*\* (`app/services/cache.py`) -- the question is hashed and checked against `cache\_entries` for an exact match. No hit, so it's embedded (3072-dim vector via `gemini-embedding-001`) and compared against past questions using cosine similarity. If something 0.82 or more similar was asked before, the cached answer returns immediately -- this is what makes repeat/near-duplicate questions come back in under 100ms instead of \~10 seconds.



2\. \*\*Difficulty routing\*\* (`app/services/classifier.py`) -- the question is classified as "simple" or "complex" based on keywords and length. "How does X work" contains an explanatory pattern, so it routes to the stronger, more expensive model (`gemini-3.6-flash`) rather than the cheap one (`gemini-3.1-flash-lite`).



3\. \*\*Semantic retrieval\*\* (`app/services/retriever.py`) -- the question is embedded and compared against every indexed code chunk in `code\_chunks` using pgvector's cosine distance. The top 5 most relevant chunks come back -- in this case, real chunks from `cache.py` itself.



4\. \*\*Compression\*\* (`app/services/compressor.py`) -- each retrieved chunk has blank lines and standalone comments stripped before being added to the prompt, cutting token count without changing meaning.



5\. \*\*LLM call\*\* -- the compressed chunks plus the question are sent to Gemini. The response, along with real token counts, comes back.



6\. \*\*Logging\*\* -- the request is saved to `request\_logs`: tokens used, calculated cost, latency, which model tier handled it, cache hit/miss.



\*\*You get back:\*\*

```json

{

&#x20; "answer": "The semantic cache works in two stages: first an exact hash match... \[full explanation, grounded in the actual code]",

&#x20; "sources": \[

&#x20;   {"file\_path": "app/services/cache.py", "chunk\_name": "get\_cached\_response", "similarity": 0.63},

&#x20;   {"file\_path": "app/services/cache.py", "chunk\_name": "save\_to\_cache", "similarity": 0.58}

&#x20; ],

&#x20; "latency\_ms": 3269,

&#x20; "tier": "complex",

&#x20; "model\_used": "gemini-3.6-flash"

}

```



Notice the `sources` field -- you can see exactly which pieces of code the answer is grounded in, so you can verify it isn't hallucinating.



\*\*Ask the exact same question again\*\*, and instead of repeating steps 2-5, it hits the cache in step 1 and returns in \~50ms with `"cached": true` -- no LLM call, no cost, same accurate answer.



\---



\## Results Achieved



\*\*Retrieval quality:\*\* questions about the codebase returned relevant chunks with similarity scores 0.55-0.68. An off-topic question ("What is the weather today?") correctly scored lower (0.50-0.53) and the model said it had no relevant information rather than hallucinating.



\*\*Compression:\*\* \~3.7-5.9% token reduction, safe and conservative (only blank lines and standalone comments stripped).



\*\*Caching:\*\* exact-match repeat questions went from \~6591ms to \~54ms. Semantic cache threshold of 0.82 was chosen from real measured data (lightly reworded questions scored 0.85 similarity, heavily reworded scored 0.94, genuinely different questions scored 0.79).



\*\*Model routing:\*\* simple questions routed to `gemini-3.1-flash-lite` ($0.25/M input, $1.50/M output), complex questions to `gemini-3.6-flash` ($0.75/M input, $3.75/M output) -- confirmed via real cost differences in the dashboard.



\*\*Deployment:\*\* fully live on Render, verified with real HTTP requests against the public URL, including full semantic retrieval working against the cloud database.



\---



\## Phase 1 -- Foundation



\- \*\*1.1\*\* Project structure, FastAPI skeleton

\- \*\*1.2\*\* PostgreSQL + pgvector, via official Docker image `pgvector/pgvector:pg16` (avoided third-party Windows binaries and Visual Studio Build Tools)

\- \*\*1.3\*\* DB models: `request\_logs`, `cache\_entries`, `code\_chunks` (SQLAlchemy, in `app/core/database.py` and `app/models/`)

\- \*\*1.4\*\* Swappable LLM client (`app/services/llm\_client.py`) -- Gemini live, Claude/OpenAI stubbed behind the same interface

\- \*\*1.5\*\* Tree-sitter AST indexer (`app/services/indexer.py`) -- parses Python into function/class chunks, not arbitrary line splits

\- \*\*1.6\*\* Embedding generation (`app/services/embedder.py`) -- `gemini-embedding-001`, 3072 dimensions

\- \*\*1.7\*\* Semantic retriever (`app/services/retriever.py`) -- pgvector cosine similarity search

\- \*\*1.8\*\* `POST /chat` endpoint -- ties indexer, retriever, LLM, and DB logging together

\- \*\*1.9\*\* End-to-end tested against the app's own source code



\## Phase 2 -- Cost/Token Dashboard



\- \*\*2.1\*\* `GET /stats` and `GET /stats/by-question` endpoints (`app/api/stats.py`)

\- \*\*2.2\*\* React dashboard (Vite-scaffolded `frontend/`) showing stat cards and a request table

\- \*\*2.3\*\* Per-question cost breakdown, delivered by the same stats endpoint

\- Real cost tracking added (`app/services/pricing.py`) using actual Gemini pricing



\## Phase 3 -- Compression



\- \*\*3.1\*\* `compress\_code()` (`app/services/compressor.py`) -- strips trailing whitespace, collapses blank lines, removes full-line comments. Does not touch inline comments or strings.

\- \*\*3.2\*\* Wired into `/chat`, applied to each retrieved chunk before building the prompt

\- \*\*3.3\*\* Measured \~3.7% reduction on a like-for-like question vs the Phase 1 baseline



\## Phase 4 -- Caching



\- \*\*4.1\*\* Exact-match cache (`cache\_entries` table, `app/services/cache.py`)

\- \*\*4.2\*\* Wired into `/chat`, checked before retrieval/compression/LLM call

\- \*\*4.3\*\* Semantic cache upgrade -- `cache\_entries.embedding` column added, two-stage lookup (exact hash, then cosine similarity with a 0.82 threshold)



\## Phase 5 -- Model Routing



\- \*\*5.1\*\* Heuristic difficulty classifier (`app/services/classifier.py`)

\- \*\*5.2\*\* Routes between `gemini-3.1-flash-lite` (simple) and `gemini-3.6-flash` (complex); Claude/OpenAI tiers stubbed for later

\- \*\*5.3\*\* Tier and actual model name logged per request, visible in the dashboard



\## Phase 6 -- Agent Loop + Verification



\- \*\*6.1\*\* File read/write tools (`app/services/file\_tools.py`)

\- \*\*6.2\*\* Test executor (`app/services/test\_executor.py`) -- runs pytest via `sys.executable`, returns structured pass/fail results

\- \*\*6.3\*\* Fix-loop (`app/services/fix\_loop.py`) -- diagnose failure, generate patch, apply, re-run tests, repeat up to 3 attempts. Verified end to end on a real bug.

\- \*\*6.4\*\* Auto-backup before any file edit (timestamped `.bak` files in `backups/`)



\## Phase 7 -- Reliability \& Auth



\- \*\*7.1\*\* Global exception handler, structured logging, clean error responses instead of raw tracebacks

\- \*\*7.2\*\* Pydantic validation on `/chat` (question length, non-blank, valid provider)

\- \*\*7.3\*\* API key auth via `X-API-Key` header (`app/core/auth.py`)

\- \*\*7.4\*\* Rate limiting via `slowapi` -- 10 requests/minute per IP, verified with real repeated requests



\## Phase 8 -- Frontend



\- \*\*8.1\*\* React chat UI (`frontend/src/ChatView.jsx`) -- real conversation thread, tier/model badges, source chips

\- \*\*8.2\*\* Dashboard merged into the same frontend as a tab

\- \*\*8.3\*\* Diff viewer for agent edits (`frontend/src/AgentView.jsx`, backend endpoint `POST /agent/fix`) -- shows a red/green line diff plus full test output, verified on a real bug fix



\## Phase 9 -- Deployment



\- \*\*9.1\*\* `Dockerfile` (Python 3.11-slim, includes build tools for psycopg2/tree-sitter) and `docker-compose.yml` (app + Postgres, healthcheck-gated startup)

\- \*\*9.2\*\* Environment config for prod vs dev (`ENVIRONMENT` variable, `.env` values only fill in variables not already set by the real environment -- critical fix for Docker/Render, since real env vars must win over stale local `.env` values baked into an image)

\- \*\*9.3\*\* Deployed live on Render: free PostgreSQL (pgvector enabled manually, expires 30 days after creation, cheap/easy to recreate), free web service built from the existing Dockerfile, all environment variables (including a rotated `API\_KEY` after the original was shared in chat) set on Render. Verified with real HTTP requests against the public URL, including full semantic retrieval against the cloud database (51 chunks re-indexed).



\---



\## Key setup notes / gotchas hit along the way



\- \*\*PATH issues on Windows:\*\* `setx` truncates PATH at 1024 characters and can silently break other tools. Prefer the GUI environment variable editor for permanent changes.

\- \*\*pgvector on native Windows Postgres\*\* was avoided entirely -- no official Windows binary exists, and building from source needs Visual Studio Build Tools. Used the official Docker image instead.

\- \*\*`python-dotenv` was intentionally removed\*\* in favor of a small hand-written `.env` parser using only Python's built-in `os` and `pathlib`.

\- \*\*Embedding model changed\*\* from the originally planned `text-embedding-004` (768-dim, not available on this account) to `gemini-embedding-001` (3072-dim). The `code\_chunks.embedding` column reflects this.

\- \*\*Docker Compose env var override bug:\*\* `.env` was unconditionally overwriting real environment variables Docker injected, causing the containerized app to try connecting to the wrong database. Fixed by making `.env` only fill in variables that aren't already set.

\- \*\*Render's free Postgres expires after 30 days\*\* (unlike the app hosting itself, which stays free indefinitely). Fine for a portfolio project; just needs periodic recreation.

\- \*\*API key rotation:\*\* the original `API\_KEY` value was shared in conversation and treated as compromised -- rotated to a new value across both local `.env` and the Render deployment.



\---



\## Environment reference



\- \*\*Local database (Docker):\*\* `postgresql://postgres:devpassword@localhost:5433/ai\_coding\_agent`

\- \*\*Start local container if stopped:\*\* `docker start pgvector-db`

\- \*\*Run server locally:\*\* `uvicorn main:app --reload` (from project root, venv active)

\- \*\*Run everything via Docker Compose:\*\* `docker compose up --build`

\- \*\*Re-index codebase:\*\* `python -m app.services.index\_pipeline`

\- \*\*Live deployment:\*\* https://ai-coding-agent-7kbo.onrender.com



\---



\## Roadmap status



\*\*Phases 1-9 (the full core build) are complete.\*\*



\*\*Optional, for later:\*\*

\- Phase 10 -- VS Code Extension

\- Phase 11 -- Custom Model (fine-tuning on usage logs)

