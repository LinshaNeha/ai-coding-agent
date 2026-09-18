"""
token_budget.py

Token Budget Manager: given a list of retrieved code chunks (already sorted
by similarity, most relevant first) and a maximum token budget, returns the
largest prefix of chunks whose compressed content fits within that budget.

Strategy: chunks arrive ordered by similarity (retriever.py sorts by cosine
distance already). We keep chunks in that order and stop adding once the
next chunk would push us over budget. This means we always favor the most
relevant chunks over less relevant ones when something has to be cut,
rather than cutting arbitrarily.
"""

from app.services.compressor import compress_code
from app.services.token_counter import count_tokens


def apply_token_budget(chunks: list[dict], budget_tokens: int) -> dict:
    """
    chunks: list of chunk dicts from Retriever.retrieve(), already ranked
            by similarity (most relevant first).
    budget_tokens: max tokens allowed for the compressed context.

    Returns a dict with:
        - "kept_chunks": the chunks that fit within budget
        - "dropped_chunks": the chunks that were cut to stay within budget
        - "total_tokens": token count of the final kept context
        - "budget_tokens": the budget that was applied
        - "over_budget_without_trim": whether the original full set would
          have exceeded the budget (i.e. whether trimming actually happened)
    """
    kept = []
    dropped = []
    running_tokens = 0

    # First, check whether the full set would fit at all, for reporting purposes
    full_context = "\n\n".join(
        f"# {c['chunk_type']} {c['chunk_name']} ({c['file_path']}:{c['start_line']}-{c['end_line']})\n{compress_code(c['content'])}"
        for c in chunks
    )
    full_tokens = count_tokens(full_context)
    over_budget_without_trim = full_tokens > budget_tokens

    for c in chunks:
        chunk_text = f"# {c['chunk_type']} {c['chunk_name']} ({c['file_path']}:{c['start_line']}-{c['end_line']})\n{compress_code(c['content'])}"
        chunk_tokens = count_tokens(chunk_text)

        # Always keep at least one chunk, even if it alone exceeds budget,
        # so we never return an empty context.
        if kept and running_tokens + chunk_tokens > budget_tokens:
            dropped.append(c)
            continue

        kept.append(c)
        running_tokens += chunk_tokens

    return {
        "kept_chunks": kept,
        "dropped_chunks": dropped,
        "total_tokens": running_tokens,
        "budget_tokens": budget_tokens,
        "over_budget_without_trim": over_budget_without_trim,
    }