# Prices in USD per 1 million tokens.
# Source: Google Cloud pricing page, Sep 2026.
# Gemini 3.6/3.7/3.8 Flash promotional pricing runs through Dec 31, 2026,
# then rises to $1.50 input / $7.50 output.
PRICING = {
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
}

DEFAULT_PRICING = {"input": 0.75, "output": 3.75}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING.get(model, DEFAULT_PRICING)
    cost = (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]
    return round(cost, 8)