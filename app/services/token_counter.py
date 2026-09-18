"""
token_counter.py

Lightweight, local token counting for measuring pipeline efficiency
(raw retrieval -> compression -> final prompt). Uses tiktoken's
cl100k_base encoding as a fast, dependency-light approximation.

This will not exactly match Gemini's own tokenizer (used for real billing,
see result["input_tokens"]/result["output_tokens"] from the LLM client),
but it is consistent across every request and every pipeline stage, which
is exactly what's needed to measure RELATIVE token savings between stages
and between benchmark runs (baseline vs +budget vs +reranking, etc).
"""

import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_encoding.encode(text))