# Prices in USD per 1 million tokens.
# Source: Google AI Studio / Google Cloud pricing pages, Sep 2026.
PRICING = {
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},       # promotional rate through Dec 31, 2026
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
}

DEFAULT_PRICING = {"input": 0.75, "output": 3.75}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model, DEFAULT_PRICING)
    cost = (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]
    return round(cost, 8)