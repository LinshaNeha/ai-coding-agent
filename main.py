import time
from fastapi import FastAPI
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.request_log import RequestLog
from app.services.retriever import Retriever
from app.services.llm_client import get_llm_client
from app.services.pricing import calculate_cost
from fastapi.middleware.cors import CORSMiddleware
from app.api.stats import router as stats_router
from app.services.compressor import compress_code
from app.services.cache import get_cached_response, save_to_cache

app = FastAPI()
app.include_router(stats_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
retriever = Retriever()


class ChatRequest(BaseModel):
    question: str
    provider: str = "gemini"


@app.get("/")
def read_root():
    return {"message": "Hello, AI Coding Agent is alive!"}


@app.post("/chat")
def chat(request: ChatRequest):
    start_time = time.time()
    db = SessionLocal()

    try:
        cached_answer = get_cached_response(db, request.question)
        if cached_answer is not None:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                endpoint="/chat",
                question=request.question,
                model_used=request.provider,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                cache_hit=True,
                status="success",
            )
            db.add(log_entry)
            db.commit()
            return {
                "answer": cached_answer,
                "sources": [],
                "latency_ms": latency_ms,
                "cached": True,
            }

        chunks = retriever.retrieve(request.question, top_k=5)

        context = "\n\n".join(
            f"# {c['chunk_type']} {c['chunk_name']} ({c['file_path']}:{c['start_line']}-{c['end_line']})\n{compress_code(c['content'])}"
            for c in chunks
        )

        prompt = f"""You are a coding assistant. Use the following code context to answer the question.

CONTEXT:
{context}

QUESTION:
{request.question}
"""

        llm = get_llm_client(request.provider)
        result = llm.generate(prompt)

        latency_ms = int((time.time() - start_time) * 1000)

        cost = calculate_cost("gemini-3.6-flash", result["input_tokens"], result["output_tokens"])

        log_entry = RequestLog(
            endpoint="/chat",
            question=request.question,
            model_used=request.provider,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=cost,
            latency_ms=latency_ms,
            cache_hit=False,
            status="success",
        )
        save_to_cache(db, request.question, result["text"])
        db.add(log_entry)
        db.commit()

        return {
            "answer": result["text"],
            "sources": [
                {"file_path": c["file_path"], "chunk_name": c["chunk_name"], "similarity": c["similarity"]}
                for c in chunks
            ],
            "latency_ms": latency_ms,
        }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        log_entry = RequestLog(
            endpoint="/chat",
            question=request.question,
            model_used=request.provider,
            latency_ms=latency_ms,
            status="error",
        )
        db.add(log_entry)
        db.commit()
        raise

    finally:
        db.close()