# Heuristic task-difficulty classifier.
# Routes simple/factual questions to a cheap model, and anything requiring
# real reasoning or explanation to a stronger one.

COMPLEX_KEYWORDS = [
    "explain", "why", "how does", "compare", "design", "architecture",
    "analyze", "debug", "refactor", "optimize", "trade-off", "tradeoff",
    "difference between", "walk me through", "step by step", "pros and cons",
]

SIMPLE_KEYWORDS = [
    "what is", "what are", "list", "show", "name", "define", "when",
]


def classify_difficulty(question: str) -> str:
    """Returns 'simple' or 'complex'."""
    q = question.lower().strip()
    word_count = len(q.split())

    if any(kw in q for kw in COMPLEX_KEYWORDS):
        return "complex"

    if any(kw in q for kw in SIMPLE_KEYWORDS) and word_count <= 12:
        return "simple"

    if word_count <= 6:
        return "simple"

    if word_count >= 15:
        return "complex"

    return "simple"


TIER_MODELS = {
    "simple": "gemini-3.1-flash-lite",
    "complex": "gemini-3.6-flash",
}


def get_model_for_question(question: str) -> tuple[str, str]:
    """Returns (tier, model_name)."""
    tier = classify_difficulty(question)
    return tier, TIER_MODELS[tier]