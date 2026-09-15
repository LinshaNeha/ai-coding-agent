import hashlib
from datetime import datetime, timezone
from app.models.cache_entry import CacheEntry
from app.services.embedder import Embedder

# Cosine similarity threshold for treating a past question as "close enough"
# to reuse its cached answer. 1.0 = identical, 0.0 = unrelated.
# Start here and tune based on real near-duplicate pairs you see in practice.
SEMANTIC_SIMILARITY_THRESHOLD = 0.82

embedder = Embedder()


def hash_query(text: str) -> str:
    """Creates a stable hash of a question, used as the exact-match cache key."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_response(db, query_text: str) -> str | None:
    """
    Returns a cached response if this question (or a near-duplicate of it)
    was asked before, else None.

    Checks in two stages:
      1. Exact hash match (fast, no embedding call needed)
      2. Semantic match via cosine similarity on stored embeddings
    """
    query_hash = hash_query(query_text)
    entry = db.query(CacheEntry).filter(CacheEntry.query_hash == query_hash).first()

    if entry:
        entry.hit_count += 1
        entry.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return entry.response_text

    # No exact match — fall back to semantic search over past questions.
    query_embedding = embedder.embed_text(query_text)

    result = (
        db.query(
            CacheEntry,
            CacheEntry.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .filter(CacheEntry.embedding.isnot(None))
        .order_by(CacheEntry.embedding.cosine_distance(query_embedding))
        .first()
    )

    if result is not None:
        entry, distance = result
        similarity = 1 - distance
        print(f"[semantic cache] closest match similarity={similarity:.4f} "
              f"(threshold={SEMANTIC_SIMILARITY_THRESHOLD}) "
              f"query={query_text!r} matched_query={entry.query_text!r}", flush=True)
        if similarity >= SEMANTIC_SIMILARITY_THRESHOLD:
            entry.hit_count += 1
            entry.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return entry.response_text

    return None


def save_to_cache(db, query_text: str, response_text: str):
    """Stores a new question/response pair in the cache, including its embedding
    so future semantically similar questions can be matched against it."""
    query_hash = hash_query(query_text)

    existing = db.query(CacheEntry).filter(CacheEntry.query_hash == query_hash).first()
    if existing:
        return  # already cached, nothing to do

    query_embedding = embedder.embed_text(query_text)

    entry = CacheEntry(
        query_hash=query_hash,
        query_text=query_text,
        response_text=response_text,
        embedding=query_embedding,
    )
    db.add(entry)
    db.commit()