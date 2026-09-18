"""
reranker_cross_encoder_EXPERIMENTAL.py

NOT CURRENTLY USED IN PRODUCTION. This is the cross-encoder-based reranker,
tested and verified working correctly on local development (see conversation/
commit history), but NOT deployed to Render: sentence-transformers pulls in
torch as a dependency, and torch's import/startup overhead was slow enough
to blow past Render's port-binding timeout on the free tier (deploy failed
after ~18 minutes with "Port scan timeout reached, no open ports detected").

This is kept in the repo, unused, as a record of the better-but-infeasible
approach: cross-encoders score the (question, chunk) pair jointly rather
than comparing separately-computed embeddings, which is generally more
accurate than the keyword-overlap heuristic actually deployed
(see reranker.py). If this project is ever moved to a paid hosting tier
with more startup time / memory headroom, this file can replace reranker.py
directly -- both expose the same rerank_chunks(question, chunks, top_n)
signature, so main.py would need no changes beyond the import line.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~90MB, CPU-only, no external
API call). Requires: pip install sentence-transformers
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
        - "scores": list of (chunk_name, cross_encoder_score) for the kept chunks
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