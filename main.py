import time
import logging
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import SessionLocal
from app.core.auth import verify_api_key
from app.models.request_log import RequestLog
from app.services.retriever import Retriever
from app.services.llm_client import get_llm_client
from app.services.pricing import calculate_cost
from fastapi.middleware.cors import CORSMiddleware
from app.api.stats import router as stats_router
from app.services.compressor import compress_code
from app.services.cache import get_cached_response, save_to_cache
from app.services.classifier import get_model_for_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_coding_agent")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(stats_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
retriever = Retriever()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    provider: str = "gemini"

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question cannot be blank or only whitespace")
        return v

    @field_validator("provider")
    @classmethod
    def provider_must_be_known(cls, v: str) -> str:
        allowed = {"gemini", "claude", "openai"}
        if v not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. This has been logged."},
    )


@app.get("/")
def read_root():
    return {"message": "Hello, AI Coding Agent is alive!"}


@app.post("/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def chat(request: Request, body: ChatRequest):
    start_time = time.time()
    db = SessionLocal()

    try:
        cached_answer = get_cached_response(db, body.question)
        if cached_answer is not None:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = RequestLog(
                endpoint="/chat",
                question=body.question,
                model_used=body.provider,
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

        tier, model_name = get_model_for_question(body.question)

        chunks = retriever.retrieve(body.question, top_k=5)

        context = "\n\n".join(
            f"# {c['chunk_type']} {c['chunk_name']} ({c['file_path']}:{c['start_line']}-{c['end_line']})\n{compress_code(c['content'])}"
            for c in chunks
        )

        prompt = f"""You are a coding assistant. Use the following code context to answer the question.

CONTEXT:
{context}

QUESTION:
{body.question}
"""

        llm = get_llm_client(body.provider, model=model_name)
        result = llm.generate(prompt)

        latency_ms = int((time.time() - start_time) * 1000)

        cost = calculate_cost(model_name, result["input_tokens"], result["output_tokens"])

        log_entry = RequestLog(
            endpoint="/chat",
            question=body.question,
            model_used=model_name,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=cost,
            latency_ms=latency_ms,
            cache_hit=False,
            status="success",
        )
        save_to_cache(db, body.question, result["text"])
        db.add(log_entry)
        db.commit()

        return {
            "answer": result["text"],
            "sources": [
                {"file_path": c["file_path"], "chunk_name": c["chunk_name"], "similarity": c["similarity"]}
                for c in chunks
            ],
            "latency_ms": latency_ms,
            "tier": tier,
            "model_used": model_name,
        }

    except HTTPException:
        raise

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception("Error in /chat")
        log_entry = RequestLog(
            endpoint="/chat",
            question=body.question,
            model_used=body.provider,
            latency_ms=latency_ms,
            status="error",
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to process chat request")

    finally:
        db.close()