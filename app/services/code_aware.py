"""
code_aware.py

Code-aware context expansion: given a set of already-selected chunks (post
reranking/budgeting), scans each chunk's content for function calls and pulls
in any OTHER indexed chunk that defines a called function, if it isn't
already selected. This helps answer questions like "if I change retrieve(),
what else breaks?" by including callees the LLM would otherwise not see.

This is computed on-the-fly per request (not precomputed at index time), by
matching identifier-followed-by-"(" patterns against known chunk_names in
the database. This avoids needing a schema change or a full re-index, at the
cost of a small amount of extra per-request work.
"""

import re

from app.core.database import SessionLocal
from app.models.code_chunk import CodeChunk

# Common Python builtins / stdlib calls we don't want to chase as "callees",
# since they're not part of this codebase and would just add noise.
_IGNORED_CALLS = {
    "print", "len", "str", "int", "float", "bool", "list", "dict", "set",
    "tuple", "range", "enumerate", "zip", "map", "filter", "sorted", "sum",
    "min", "max", "abs", "round", "open", "isinstance", "type", "super",
    "getattr", "setattr", "hasattr", "property", "staticmethod", "classmethod",
    "Exception", "ValueError", "TypeError", "KeyError", "ImportError",
    "format", "join", "split", "strip", "append", "extend", "get", "items",
    "keys", "values", "field_validator", "classmethod", "Field", "BaseModel",
}

_CALL_PATTERN = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def _extract_call_names(content: str) -> set[str]:
    names = set(_CALL_PATTERN.findall(content))
    return {n for n in names if n not in _IGNORED_CALLS and not n.startswith("_")}


def expand_with_callees(chunks: list[dict], max_extra_chunks: int = 3) -> dict:
    """
    chunks: the currently-selected chunks (post rerank/budget).
    max_extra_chunks: cap on how many additional callee chunks to pull in,
                       to avoid unbounded context growth.

    Returns a dict with:
        - "expanded_chunks": original chunks + any newly added callee chunks
        - "added_chunks": just the newly added callee chunks
    """
    if not chunks:
        return {"expanded_chunks": chunks, "added_chunks": []}

    already_selected_names = {c["chunk_name"] for c in chunks}

    all_called_names = set()
    for c in chunks:
        all_called_names |= _extract_call_names(c["content"])

    candidate_names = all_called_names - already_selected_names
    if not candidate_names:
        return {"expanded_chunks": chunks, "added_chunks": []}

    db = SessionLocal()
    try:
        matches = (
            db.query(CodeChunk)
            .filter(CodeChunk.chunk_name.in_(candidate_names))
            .limit(max_extra_chunks)
            .all()
        )

        added = [
            {
                "file_path": m.file_path,
                "chunk_type": m.chunk_type,
                "chunk_name": m.chunk_name,
                "content": m.content,
                "start_line": m.start_line,
                "end_line": m.end_line,
                "similarity": 0.0,  # not retrieved by similarity; added via call-graph
            }
            for m in matches
        ]

        return {
            "expanded_chunks": chunks + added,
            "added_chunks": added,
        }
    finally:
        db.close()