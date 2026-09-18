"""
llmlingua_experiment.py

Standalone LOCAL-ONLY experiment: measures how much additional token
reduction LLMLingua-2 could provide on top of the already-deployed
pipeline (retrieve -> rerank -> code-aware expand -> token budget ->
compress_code). This is NOT wired into main.py and NOT deployed --
LLMLingua-2 requires torch/transformers and an ~1.2GB model, which (based
on the cross-encoder reranker's failed Render deploy) would almost
certainly fail the same way on Render's free tier.

This script exists purely to get real, measured evidence of LLMLingua-2's
impact, even though it can't run in production -- the same way the
cross-encoder was proven locally before we learned it couldn't deploy.

Usage:
    python eval/llmlingua_experiment.py

Run from the project root, venv active, LOCAL Docker DB running
(docker start pgvector-db) since it calls the real retriever.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os

from app.services.retriever import Retriever
from app.services.reranker_cross_encoder_EXPERIMENTAL import rerank_chunks
from app.services.code_aware import expand_with_callees
from app.services.token_budget import apply_token_budget
from app.services.compressor import compress_code
from app.services.token_counter import count_tokens

RETRIEVE_TOP_K = 12
RERANK_TOP_N = 6
MAX_CALLEE_CHUNKS = 3
TOKEN_BUDGET = 800

QUESTIONS_PATH = os.path.join("eval", "questions.json")
RESULTS_PATH = os.path.join("eval", "results", "llmlingua_experiment.json")


def build_pipeline_context(question: str, retriever: Retriever) -> str:
    """Reproduces the exact same pipeline main.py uses, up through compression,
    so we're testing LLMLingua-2 on the SAME context that's actually deployed."""
    chunks = retriever.retrieve(question, top_k=RETRIEVE_TOP_K)
    rerank_result = rerank_chunks(question, chunks, top_n=RERANK_TOP_N)
    reranked_chunks = rerank_result["reranked_chunks"]
    expansion_result = expand_with_callees(reranked_chunks, max_extra_chunks=MAX_CALLEE_CHUNKS)
    expanded_chunks = expansion_result["expanded_chunks"]
    budget_result = apply_token_budget(expanded_chunks, TOKEN_BUDGET)
    final_chunks = budget_result["kept_chunks"]

    context = "\n\n".join(
        f"# {c['chunk_type']} {c['chunk_name']} ({c['file_path']}:{c['start_line']}-{c['end_line']})\n{compress_code(c['content'])}"
        for c in final_chunks
    )
    return context


def load_questions(path, limit=5):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flat = []
    for category, items in data.get("categories", {}).items():
        for item in items:
            if item["question"].strip().upper().startswith("PLACEHOLDER"):
                continue
            flat.append({"category": category, **item})
    return flat[:limit]


def main():
    print("Loading LLMLingua-2 compressor (this downloads ~1.2GB on first run)...")
    from llmlingua import PromptCompressor

    llm_lingua = PromptCompressor(
        model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
        use_llmlingua2=True,
        device_map="cpu",
    )
    print("Loaded.\n")

    retriever = Retriever()
    questions = load_questions(QUESTIONS_PATH, limit=5)  # small sample -- this is slow

    results = []

    for q in questions:
        print(f"Processing: {q['question'][:60]}...")

        pre_llmlingua_context = build_pipeline_context(q["question"], retriever)
        pre_tokens = count_tokens(pre_llmlingua_context)

        if not pre_llmlingua_context.strip():
            print("  (empty context, skipping)")
            continue

        compressed = llm_lingua.compress_prompt(
            pre_llmlingua_context,
            rate=0.6,  # keep ~60% of tokens
            force_tokens=["\n", "#"],
        )
        post_text = compressed["compressed_prompt"]
        post_tokens = count_tokens(post_text)

        reduction_pct = (100 * (pre_tokens - post_tokens) / pre_tokens) if pre_tokens else 0.0

        print(f"  pre={pre_tokens} tokens -> post={post_tokens} tokens ({reduction_pct:.1f}% additional reduction)\n")

        results.append({
            "id": q["id"],
            "question": q["question"],
            "pre_llmlingua_tokens": pre_tokens,
            "post_llmlingua_tokens": post_tokens,
            "additional_reduction_pct": round(reduction_pct, 2),
        })

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"note": "LOCAL EXPERIMENT ONLY -- not deployed, see README", "results": results}, f, indent=2)

    avg_reduction = sum(r["additional_reduction_pct"] for r in results) / len(results) if results else 0
    print(f"\nDone. Average additional reduction from LLMLingua-2: {avg_reduction:.1f}%")
    print(f"Saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()