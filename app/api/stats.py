from fastapi import APIRouter
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.request_log import RequestLog

router = APIRouter()


@router.get("/stats")
def get_stats():
    db = SessionLocal()
    try:
        total_requests = db.query(func.count(RequestLog.id)).scalar() or 0
        total_cost = db.query(func.sum(RequestLog.cost_usd)).scalar() or 0.0
        total_input_tokens = db.query(func.sum(RequestLog.input_tokens)).scalar() or 0
        total_output_tokens = db.query(func.sum(RequestLog.output_tokens)).scalar() or 0
        avg_latency_ms = db.query(func.avg(RequestLog.latency_ms)).scalar() or 0
        cache_hits = db.query(func.count(RequestLog.id)).filter(RequestLog.cache_hit == True).scalar() or 0
        errors = db.query(func.count(RequestLog.id)).filter(RequestLog.status == "error").scalar() or 0

        cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 6),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "avg_latency_ms": round(avg_latency_ms, 1),
            "cache_hits": cache_hits,
            "cache_hit_rate_pct": round(cache_hit_rate, 1),
            "errors": errors,
        }
    finally:
        db.close()


@router.get("/stats/by-question")
def get_stats_by_question(limit: int = 20):
    db = SessionLocal()
    try:
        logs = (
            db.query(RequestLog)
            .order_by(RequestLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "question": log.question,
                "model_used": log.model_used,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "cost_usd": log.cost_usd,
                "latency_ms": log.latency_ms,
                "status": log.status,
            }
            for log in logs
        ]
    finally:
        db.close()