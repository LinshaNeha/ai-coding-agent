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
## Phase 10 -- VS Code Extension

- **10.1** Extension scaffolded in vscode-extension/ (extension.js, package.json) -- registers an "AI Coding Agent" command, prompts for a question, and calls the deployed /chat endpoint

- **10.2** Settings for Api Url (pre-filled with the Render deployment) and Api Key, stored via VS Code's own settings (no key hardcoded in source)

- **10.3** Verified end to end in the Extension Development Host: command registers correctly, correctly errors when no API key is set, and after entering a key, returns real grounded answers with sources -- both a semantic-cache hit (~135ms) and a genuine live LLM call (~17s, correct tier/model routing) were confirmed

## Phase 12 -- Adaptive Token Efficiency

Motivation: Phases 1-9 already showed real cost reduction from retrieval + output constraints, compression, caching, and model routing (see Results Achieved above). Phase 12 goes further -- instead of always sending a fixed top-k of retrieved chunks, the pipeline now dynamically narrows and enriches context before it ever reaches the LLM, with every stage measured in tokens so the tradeoffs are visible rather than assumed.

- **12.1** Explicit token counting at every pipeline stage (app/services/token_counter.py) -- uses tiktoken's cl100k_base encoding as a fast, free, local approximation. This does not exactly match Gemini's own tokenizer (the real billed counts still come from the LLM response itself), but it's consistent across every stage and every run, which is what's needed to compare raw vs. compressed vs. final prompt sizes, and to compare pipeline versions against each other.

- **12.2** Token Budget Manager (app/services/token_budget.py) -- given a maximum token budget (currently 800), keeps chunks in similarity/relevance order and drops the lowest-ranked ones once the running total would exceed budget, always keeping at least one chunk. This replaced a fixed top_k=5 cutoff with a cutoff based on actual context size, which matters once retrieval, reranking, and code-aware expansion can all vary how much context comes back.

- **12.3** Retrieval widened + reranking (app/services/reranker.py) -- retrieval now pulls a larger candidate pool (top_k=12, up from 5) via the existing pgvector bi-encoder search, then a second pass reranks those candidates before the token budget is applied. Two reranking approaches were built and compared:

  - **Cross-encoder (tried first, not deployed):** cross-encoder/ms-marco-MiniLM-L-6-v2 (~90MB, CPU-only), which scores the (question, chunk) pair jointly rather than comparing separately-computed embeddings -- generally more accurate than bi-encoder similarity alone, since it can attend to the question and the code together. Verified working correctly on local development. Deployment to Render failed after ~18 minutes: `sentence-transformers` pulls in `torch`, and torch's import/startup overhead was slow enough to exceed Render's port-binding timeout on the free tier (`Port scan timeout reached, no open ports detected`), even with the model loaded lazily on first request rather than at startup. This is a real infrastructure constraint, not a flaw in the approach -- the code is kept, unused, in `app/services/reranker_cross_encoder_EXPERIMENTAL.py` as a direct drop-in replacement for `reranker.py` (same `rerank_chunks(question, chunks, top_n)` signature) if this project ever moves to a paid tier with more memory/startup headroom.

  - **Heuristic (currently deployed):** `app/services/reranker.py` combines the existing bi-encoder similarity score with a keyword-overlap boost -- chunks whose name or content share more words with the question rank higher, with name matches weighted more heavily than content matches. No extra dependency, no extra latency, no extra per-request cost, deploys cleanly on the free tier. A real but weaker relevance signal than the cross-encoder.

  An LLM-as-reranker approach was also considered and deliberately rejected for both versions: it would add a second paid LLM call per request, working against the cost-efficiency goal of this whole phase.

  **Evidence:** the cross-encoder was verified working correctly on local development --

  <img width="1087" height="318" alt="Screenshot 2026-09-18 144648" src="https://github.com/user-attachments/assets/71bf378b-6119-4b96-ac63-c33698747e6f" />


  *(sentence-transformers imports successfully, the model loads, and correctly ranks a `retrieve`-related chunk above an unrelated `compress_code` chunk for the question "what does the retriever do", with a real relevance score returned.)*

  Deployment to Render failed after ~18 minutes with a port-binding timeout, confirming the constraint was infrastructure, not the technique.

  *(Render's own build log: "Port scan timeout reached, no open ports detected" -- torch's import/startup overhead was too slow for the free tier's health check window.)*
- **12.4** Code-aware context expansion (app/services/code_aware.py) -- after reranking, each kept chunk's content is scanned for function-call patterns; any called function that has its own indexed chunk (and isn't already selected) gets pulled in, up to a small cap, so questions like "what breaks if I rename X" can see the actual callees rather than just the chunk that was semantically closest to the question text. This is computed at query time by matching against existing chunk_name values already stored in code_chunks, rather than precomputing and storing a call graph at index time -- avoiding a schema change or a full re-index at the cost of a small amount of extra per-request computation.

- **12.5 (bug found & fixed)** Initial implementation applied the token budget *before* code-aware expansion, so the callee chunks added in 12.4 could push the final context back over budget (observed: budget=800, but final compressed context measured 1149 tokens). Fixed by reordering the pipeline so the token budget is applied last, after expansion, making it the true final gate on what gets sent to the LLM. Verified afterward: a case that previously would have been ~2144 raw tokens across 12 chunks came down to 802 compressed tokens across 3 final chunks (reranked + 3 callees added, then budgeted) -- about a 63% reduction, while the answer remained grounded in real, correctly-identified source chunks.

- **Pipeline order (current):** retrieve top 12 (pgvector) -> rerank to top 6 (cross-encoder) -> expand with up to 3 callees (code-aware) -> apply token budget of 800 (drops lowest-relevance chunks first) -> compress (existing compress_code) -> build prompt -> LLM call.

- **Still to do:** LLMLingua-2 as an optional second-stage compressor if context is still large after the above (needs a feasibility check on Render's free tier, given it's an additional ML model); then a full ablation benchmark (baseline vs +budget vs +reranking vs +code-aware vs +LLMLingua-2) across a fixed 18-question eval set (eval/questions.json), comparing input/output tokens, cost, latency, and answer quality/groundedness at each stage.

- **Gotcha:** sentence-transformers (needed for the cross-encoder) pulls in torch as a dependency, which is a much heavier install than anything used in Phases 1-9. Feasibility on Render's free tier (build time, memory) still needs to be confirmed after deployment.

- **12.6** LLMLingua-2 -- evaluated as a local-only experiment (eval/llmlingua_experiment.py), not deployed. Deployment was ruled out up front: LLMLingua-2 requires an xlm-roberta-large-based model (~1.2GB) plus torch/transformers, the same class of dependency that had just failed to deploy on Render's free tier for the (much smaller, ~90MB) cross-encoder reranker in 12.3, which missed Render's port-binding timeout after ~18 minutes.

  Rather than stop at that prediction, LLMLingua-2 was still installed and run locally against the real, already-optimized pipeline output (post retrieval + rerank + code-aware expansion + token budget + compress_code) for 5 real questions against this codebase. Result: an average of **43.6% additional token reduction** on top of what the existing pipeline already achieved (e.g. one question's context went from 787 tokens post-pipeline down to 441 tokens after LLMLingua-2, a 44% further cut). This is real, measured evidence that meaningful additional compression is available -- it's a hosting constraint that rules it out here, not a limitation of the technique itself. Full results in eval/results/llmlingua_experiment.json.
  <img width="1070" height="560" alt="Screenshot 2026-09-18 143514" src="https://github.com/user-attachments/assets/0cfaba5e-f2b9-4c7f-b2a4-d0f41e785051" />


  **Known limitation observed:** one question's context (1147 tokens) exceeded LLMLingua-2's underlying model's 512-token max sequence length, triggering a truncation warning -- that result should be treated as less reliable than the others, and a real deployment would need chunk-level (not whole-context) compression to avoid this.


## Phase 12 -- Final Results

A note on methodology: the original baseline benchmark (eval/results/baseline.json) was captured before per-stage token counting existed (12.1), so it has real latency/tier/cache data but no token breakdown to compare against directly. Rather than roll the live pipeline back to regenerate a "clean" side-by-side (real risk of introducing new bugs for a modest gain in tidiness), the results below are presented from the optimized pipeline's own data (eval/results/with_optimizations.json) -- which is self-evidencing: every non-cached question shows the raw retrieved context (from the wider top-12 pool) being substantially reduced before reaching the LLM.

**16/16 questions succeeded** against the live Render deployment (a handful needed one or two retries due to transient Gemini 503s under load -- an upstream provider issue, not a pipeline bug; see Phase 9 gotchas for the same pattern observed earlier).

Sample of real, non-cached results (raw vs. final compressed context, in tokens):

| Question | Raw tokens (top-12) | Compressed (final) | Reduction |
|---|---|---|---|
| "What model is used for embeddings..." | 1433 | 433 | 70% |
| "What functions does compress_code depend on..." | 2105 | 764 | 64% |
| "How does the app decide what code is relevant..." | 2039 | 799 | 61% |
| "What happens if the LLM call fails partway..." | 1721 | 797 | 54% |
| "How does the semantic cache decide..." | 1696 | 799 | 53% |
| "What tables does the app use in the database?" | 1526 | 782 | 49% |

Full results: eval/results/with_optimizations.json. Comparison tooling: eval/compare_results.py (built to diff against a token-aware baseline if one is captured in the future).

**What this demonstrates:** widening retrieval from top-5 to top-12 gives the reranker and code-aware expansion a larger, better pool to work with -- while the token budget manager (12.2) reliably brings the final context back down to a consistent, bounded size (~750-800 tokens) regardless of how much raw material came in, without needing a fixed top-k cutoff to do it. Answers remained grounded throughout (5-8 real sources cited per question, correct call-graph expansions observed for code-aware test questions like c1/c2).
## Roadmap status

**Phases 1-10 are complete. Phase 12 (Adaptive Token Efficiency) is in progress -- token counting, budget management, reranking, and code-aware expansion are built and verified locally; LLMLingua-2 and the final benchmark are still to come.**

**Optional, for later:**

- Phase 11 -- Custom Model (fine-tuning on usage logs) -- deliberately deferred: not enough real usage volume yet to fine-tune on meaningfully, per project notes.

- **Deployment status:** built and verified locally only (Docker Postgres) as of this writing -- not yet committed/pushed or deployed to Render. Next step is a commit + push, then confirming the sentence-transformers/torch dependency (needed for the cross-encoder reranker) builds successfully on Render's free tier, since it's a notably heavier install than anything used in Phases 1-9.

\- Phase 11 -- Custom Model (fine-tuning on usage logs)

