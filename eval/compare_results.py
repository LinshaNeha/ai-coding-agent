"""
compare_results.py

Reads eval/results/baseline.json and eval/results/with_optimizations.json,
matches questions by ID, and prints a before/after comparison table.

Only compares questions that were NOT cache hits in either run, since
cache hits look identical regardless of pipeline changes (they bypass
retrieval/reranking/budgeting entirely) -- comparing them would understate
or hide the real effect of the Phase 12 optimizations.

Usage:
    python eval/compare_results.py
"""

import json
import os

RESULTS_DIR = os.path.join("eval", "results")
BASELINE_PATH = os.path.join(RESULTS_DIR, "baseline.json")
OPTIMIZED_PATH = os.path.join(RESULTS_DIR, "with_optimizations.json")


def load_results(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {r["id"]: r for r in data.get("results", [])}


def get_tokens(record):
    """Pulls actual_input_tokens/actual_output_tokens if present, else None."""
    tu = record.get("token_usage")
    if not tu:
        return None, None
    return tu.get("actual_input_tokens"), tu.get("actual_output_tokens")


def main():
    baseline = load_results(BASELINE_PATH)
    optimized = load_results(OPTIMIZED_PATH)

    common_ids = sorted(set(baseline.keys()) & set(optimized.keys()))

    print(f"{'ID':<6} {'Base In':>8} {'Opt In':>8} {'Δ In':>7} {'Base Out':>9} {'Opt Out':>8} {'Δ Out':>7} {'Base ms':>9} {'Opt ms':>8}")
    print("-" * 80)

    rows = []
    for qid in common_ids:
        b = baseline[qid]
        o = optimized[qid]

        # Skip if either was a cache hit -- not a fair comparison
        if b.get("cached") or o.get("cached"):
            continue
        if not b.get("ok") or not o.get("ok"):
            continue

        b_in, b_out = get_tokens(b)
        o_in, o_out = get_tokens(o)

        if b_in is None or o_in is None:
            continue  # baseline run predates token_usage being added

        in_delta = o_in - b_in
        out_delta = o_out - b_out

        print(f"{qid:<6} {b_in:>8} {o_in:>8} {in_delta:>+7} {b_out:>9} {o_out:>8} {out_delta:>+7} "
              f"{b.get('measured_latency_ms', 0):>9} {o.get('measured_latency_ms', 0):>8}")

        rows.append({
            "id": qid,
            "baseline_input_tokens": b_in,
            "optimized_input_tokens": o_in,
            "baseline_output_tokens": b_out,
            "optimized_output_tokens": o_out,
            "baseline_latency_ms": b.get("measured_latency_ms", 0),
            "optimized_latency_ms": o.get("measured_latency_ms", 0),
        })

    if not rows:
        print("\nNo comparable (non-cached, successful in both runs) questions found.")
        print("Note: baseline.json was likely captured before token_usage tracking existed (Phase 12.1),")
        print("so most/all baseline rows won't have token_usage data to compare against.")
        return

    avg_base_in = sum(r["baseline_input_tokens"] for r in rows) / len(rows)
    avg_opt_in = sum(r["optimized_input_tokens"] for r in rows) / len(rows)
    avg_base_out = sum(r["baseline_output_tokens"] for r in rows) / len(rows)
    avg_opt_out = sum(r["optimized_output_tokens"] for r in rows) / len(rows)
    avg_base_latency = sum(r["baseline_latency_ms"] for r in rows) / len(rows)
    avg_opt_latency = sum(r["optimized_latency_ms"] for r in rows) / len(rows)

    input_reduction_pct = 100 * (avg_base_in - avg_opt_in) / avg_base_in if avg_base_in else 0
    output_change_pct = 100 * (avg_opt_out - avg_base_out) / avg_base_out if avg_base_out else 0
    latency_change_pct = 100 * (avg_opt_latency - avg_base_latency) / avg_base_latency if avg_base_latency else 0

    print("\n" + "=" * 80)
    print(f"Compared {len(rows)} question(s) (non-cached, successful in both runs)\n")
    print(f"Average input tokens:  baseline={avg_base_in:.0f}  optimized={avg_opt_in:.0f}  "
          f"({input_reduction_pct:+.1f}%)")
    print(f"Average output tokens: baseline={avg_base_out:.0f}  optimized={avg_opt_out:.0f}  "
          f"({output_change_pct:+.1f}%)")
    print(f"Average latency (ms):  baseline={avg_base_latency:.0f}  optimized={avg_opt_latency:.0f}  "
          f"({latency_change_pct:+.1f}%)")

    summary_path = os.path.join(RESULTS_DIR, "comparison_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "compared_question_count": len(rows),
            "avg_baseline_input_tokens": round(avg_base_in, 1),
            "avg_optimized_input_tokens": round(avg_opt_in, 1),
            "input_token_change_pct": round(input_reduction_pct, 2),
            "avg_baseline_output_tokens": round(avg_base_out, 1),
            "avg_optimized_output_tokens": round(avg_opt_out, 1),
            "output_token_change_pct": round(output_change_pct, 2),
            "avg_baseline_latency_ms": round(avg_base_latency, 1),
            "avg_optimized_latency_ms": round(avg_opt_latency, 1),
            "latency_change_pct": round(latency_change_pct, 2),
            "per_question": rows,
        }, f, indent=2)

    print(f"\nSaved to {summary_path}")


if __name__ == "__main__":
    main()