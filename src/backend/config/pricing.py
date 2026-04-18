# Prices per 1M tokens (USD) — verify at https://aws.amazon.com/bedrock/pricing/
PRICING = {
    "us.anthropic.claude-sonnet-4-6-20250630-v1:0": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
    }
}

def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model_id, {"input_per_1m": 3.00, "output_per_1m": 15.00})
    return round(
        (input_tokens / 1_000_000) * p["input_per_1m"] +
        (output_tokens / 1_000_000) * p["output_per_1m"],
        6
    )
