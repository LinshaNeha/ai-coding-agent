"""
run_benchmark.py (v3)

Sends questions from eval/questions.json to the live /chat endpoint,
records the response (answer, sources, tier, model, latency, cache status,
token usage), and saves everything to eval/results/<stage_name>.json.

Usage:
    python eval/run_benchmark.py baseline
    python eval/run_benchmark.py baseline --ids s3,s4,m4,b1,b2,b3,c2
    python eval/run_benchmark.py baseline --delay 20

Run this from the project root (same folder as main.py and .env).
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

API_URL = (Render URL available on request)
ENV_PATH = ".env"
QUESTIONS_PATH = os.path.join("eval", "questions.json")
RESULTS_DIR = os.path.join("eval", "results")
DEFAULT_DELAY_SECONDS = 7


def load_api_key(env_path):
    if not os.path.exists(env_path):
        print(f"ERROR: could not find {env_path}. Run this script from the project root.")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "API_KEY":
                return value

    print("ERROR: API_KEY not found in .env")
    sys.exit(1)


def load_questions(path, only_ids=None):
    if not os.path.exists(path):
        print(f"ERROR: could not find {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flat = []
    for category, items in data.get("categories", {}).items():
        for item in items:
            if item["question"].strip().upper().startswith("PLACEHOLDER"):
                continue
            if only_ids and item["id"] not in only_ids:
                continue
            flat.append({"category": category, **item})
    return flat


def ask_question(question_text, api_key, timeout=90):
    payload = json.dumps({"question": question_text}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            elapsed_ms = round((time.time() - start) * 1000)
            return {"ok": True, "elapsed_ms": elapsed_ms, "response": json.loads(body)}
    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.time() - start) * 1000)
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except Exception as e:
        elapsed_ms = round((time.time() - start) * 1000)
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": str(e)}


def build_record(q, outcome):
    record = {
        "id": q["id"],
        "category": q["category"],
        "question": q["question"],
    }
    if outcome["ok"]:
        resp = outcome["response"]
        record.update({
            "ok": True,
            "measured_latency_ms": outcome["elapsed_ms"],
            "reported_latency_ms": resp.get("latency_ms"),
            "tier": resp.get("tier"),
            "model_used": resp.get("model_used"),
            "cached": resp.get("cached", False),
            "num_sources": len(resp.get("sources", [])),
            "sources": resp.get("sources", []),
            "answer_length_chars": len(resp.get("answer", "")),
            "answer": resp.get("answer"),
            "token_usage": resp.get("token_usage"),
        })
    else:
        record.update({
            "ok": False,
            "measured_latency_ms": outcome["elapsed_ms"],
            "error": outcome["error"],
        })
    return record


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python eval/run_benchmark.py <stage_name> [--ids id1,id2,...] [--delay N]")
        sys.exit(1)

    stage_name = args[0]
    only_ids = None
    delay_seconds = DEFAULT_DELAY_SECONDS

    i = 1
    while i < len(args):
        if args[i] == "--ids" and i + 1 < len(args):
            only_ids = set(x.strip() for x in args[i + 1].split(","))
            i += 2
        elif args[i] == "--delay" and i + 1 < len(args):
            delay_seconds = float(args[i + 1])
            i += 2
        else:
            i += 1

    api_key = load_api_key(ENV_PATH)
    questions = load_questions(QUESTIONS_PATH, only_ids=only_ids)

    if not questions:
        print("No matching questions found. Check your --ids values against eval/questions.json.")
        sys.exit(1)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    output_path = os.path.join(RESULTS_DIR, f"{stage_name}.json")

    existing_results_by_id = {}
    if only_ids and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing_summary = json.load(f)
        for r in existing_summary.get("results", []):
            existing_results_by_id[r["id"]] = r
        print(f"Loaded existing results from {output_path} ({len(existing_results_by_id)} entries) — will merge.\n")
    elif only_ids:
        print(f"No existing {output_path} found — will create fresh with only the retried IDs.\n")

    print(f"Running {len(questions)} question(s) against {API_URL} (delay={delay_seconds}s)")
    print(f"Results will be saved to {output_path}\n")

    for idx, q in enumerate(questions, 1):
        print(f"[{idx}/{len(questions)}] ({q['category']}/{q['id']}) {q['question'][:70]}...")
        outcome = ask_question(q["question"], api_key)
        record = build_record(q, outcome)

        if record.get("ok"):
            tu = record.get("token_usage") or {}
            print(f"    -> {record['measured_latency_ms']}ms | tier={record['tier']} | model={record['model_used']} | cached={record['cached']} | sources={record['num_sources']}")
            if tu:
                print(f"       tokens: raw={tu.get('raw_context_tokens')} compressed={tu.get('compressed_context_tokens')} "
                      f"prompt_est={tu.get('prompt_tokens_local_estimate')} actual_in={tu.get('actual_input_tokens')} actual_out={tu.get('actual_output_tokens')}")
        else:
            print(f"    -> ERROR: {record['error']}")

        existing_results_by_id[q["id"]] = record

        if idx < len(questions):
            time.sleep(delay_seconds)

    final_results = list(existing_results_by_id.values())

    summary = {
        "stage_name": stage_name,
        "api_url": API_URL,
        "total_questions": len(final_results),
        "successful": sum(1 for r in final_results if r.get("ok")),
        "failed": sum(1 for r in final_results if not r.get("ok")),
        "cached_hits": sum(1 for r in final_results if r.get("cached")),
        "results": final_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone. {summary['successful']}/{summary['total_questions']} succeeded, "
          f"{summary['cached_hits']} cache hits.")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
