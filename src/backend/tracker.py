from datetime import datetime, timezone
from config.settings import FIRESTORE_TOKEN_LOGS
from config.pricing import calculate_cost


def log_usage(
    db,
    employee_email: str,
    doc_id: str,
    lor_type: str,
    input_tokens: int,
    output_tokens: int,
    model_id: str,
) -> float:
    cost = calculate_cost(model_id, input_tokens, output_tokens)
    db.collection(FIRESTORE_TOKEN_LOGS).add({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "employee_email": employee_email,
        "doc_id": doc_id,
        "lor_type": lor_type,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "model_id": model_id,
    })
    return cost
