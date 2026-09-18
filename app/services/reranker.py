"""
reranker.py

Reranks retrieved code chunks using a cross-encoder model, which scores
the (question, chunk) pair jointly rather than comparing separately-computed
embeddings (what the bi-encoder retriever already does via cosine similarity).
Cross-encoders are typically more accurate at judging true relevance because
they can directly attend to both texts together, at the cost of being slower
per-comparison -- which is why we only rerank a modest candidate pool (e.g.
12 chunks from the retriever) rather than the whole codebase.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 -- a small, well-established
cross-encoder (~80MB) trained for passage reranking. Runs on CPU, no GPU
required, and needs no external API call (unlike an LLM-as-reranker
approach), which keeps this free per-request.
"""

from sentence_transformers import CrossEncoder

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def rerank_chunks(question: str, chunks: list[dict], top_n: int) -> dict:
    """
    question: the user's question.
    chunks: candidate chunks from Retriever.retrieve(), each with a 'content' field.
    top_n: how many chunks to keep after reranking.

    Returns a dict with:
        - "reranked_chunks": the top_n chunks, reordered by cross-encoder score
        - "dropped_chunks": chunks that were not kept
        - "scores": list of (chunk_name, cross_encoder_score) for the kept chunks,
          for logging/debugging
    """
    if not chunks:
        return {"reranked_chunks": [], "dropped_chunks": [], "scores": []}

    model = _get_model()

    pairs = [(question, c["content"]) for c in chunks]
    scores = model.predict(pairs)

    scored_chunks = list(zip(chunks, scores))
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    kept = [c for c, _ in scored_chunks[:top_n]]
    dropped = [c for c, _ in scored_chunks[top_n:]]
    score_log = [(c["chunk_name"], float(s)) for c, s in scored_chunks[:top_n]]

    return {
        "reranked_chunks": kept,
        "dropped_chunks": dropped,
        "scores": score_log,
    }