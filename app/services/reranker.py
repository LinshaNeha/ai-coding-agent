"""
reranker.py (v2 -- heuristic, no ML model)

A cross-encoder-based reranker (sentence-transformers + torch) was tried
first, but failed to deploy on Render's free tier: torch's import/startup
overhead was slow enough to blow past Render's port-binding timeout, even
with the model loaded lazily on first request rather than at startup. See
README Phase 12 notes for details. That version is preserved, unused, in
app/services/reranker_cross_encoder_EXPERIMENTAL.py.

This version reranks using a lightweight heuristic instead: it combines the
existing bi-encoder similarity score (from pgvector cosine distance) with a
keyword-overlap boost -- chunks whose name or content share more words with
the question get ranked higher. This is a real, if less sophisticated,
signal: a chunk literally named after a term in the question is often
genuinely more relevant than one that's merely embedding-similar. No extra
dependency, no extra latency, no extra cost per request.
"""

import re

_WORD_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Common words that don't carry much signal for matching a question to code.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "does", "do", "what", "how", "why",
    "when", "where", "which", "this", "that", "it", "and", "or", "of",
    "to", "in", "for", "on", "with", "if", "i", "you", "your", "my",
}


def _extract_keywords(text: str) -> set[str]:
    words = _WORD_PATTERN.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def rerank_chunks(question: str, chunks: list[dict], top_n: int) -> dict:
    """
    question: the user's question.
    chunks: candidate chunks from Retriever.retrieve(), each with 'content',
            'chunk_name', and 'similarity' (bi-encoder cosine similarity).
    top_n: how many chunks to keep after reranking.

    Returns a dict with:
        - "reranked_chunks": the top_n chunks, reordered by heuristic score
        - "dropped_chunks": chunks that were not kept
        - "scores": list of (chunk_name, heuristic_score) for the kept chunks
    """
    if not chunks:
        return {"reranked_chunks": [], "dropped_chunks": [], "scores": []}

    question_keywords = _extract_keywords(question)

    scored = []
    for c in chunks:
        name_keywords = _extract_keywords(c.get("chunk_name", ""))
        content_keywords = _extract_keywords(c.get("content", ""))

        name_overlap = len(question_keywords & name_keywords)
        content_overlap = len(question_keywords & content_keywords)

        # Name matches count more than content matches -- a chunk literally
        # named after something in the question is a strong relevance signal.
        keyword_boost = (name_overlap * 0.15) + (min(content_overlap, 5) * 0.03)

        base_similarity = c.get("similarity", 0.0)
        heuristic_score = base_similarity + keyword_boost

        scored.append((c, heuristic_score))

    scored.sort(key=lambda x: x[1], reverse=True)

    kept = [c for c, _ in scored[:top_n]]
    dropped = [c for c, _ in scored[top_n:]]
    score_log = [(c["chunk_name"], round(float(s), 4)) for c, s in scored[:top_n]]

    return {
        "reranked_chunks": kept,
        "dropped_chunks": dropped,
        "scores": score_log,
    }