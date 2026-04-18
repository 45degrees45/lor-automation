import json
from datetime import datetime, timezone
from gdocs import read_doc_text, read_doc_comments, extract_doc_id
from rag import index_letter
from rules import get_rules, save_rules
from aws_auth import get_bedrock_client
from config.settings import BEDROCK_MODEL_ID


def detect_lor_type(text: str) -> str:
    text_upper = text.upper()
    if "EB-1A" in text_upper or "EB1A" in text_upper:
        return "EB1A"
    if "NIW" in text_upper or "NATIONAL INTEREST" in text_upper:
        return "NIW"
    if "O-1A" in text_upper or "O1A" in text_upper:
        return "O1A"
    return "EB1A"


def summarize_comments_to_rules(comments: list, lor_type: str, existing_rules: list) -> list:
    comment_texts = [c["content"] for c in comments if not c.get("resolved")]
    if not comment_texts:
        return existing_rules

    client = get_bedrock_client()
    prompt = f"""You are analyzing team lead feedback comments on immigration LOR drafts ({lor_type} type).

Existing writing rules:
{chr(10).join(f"- {r}" for r in existing_rules) or "None yet."}

New comments from team lead:
{chr(10).join(f"- {c}" for c in comment_texts)}

Produce an updated list of 5-15 clear, actionable writing rules for {lor_type} letters.
Merge new insights with existing rules. Remove duplicates. Be specific and concrete.
Return ONLY a JSON array of strings, no other text.
Example: ["Rule 1", "Rule 2"]"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    result = json.loads(response["body"].read())
    text = result["content"][0]["text"].strip()

    try:
        return json.loads(text)
    except Exception:
        return existing_rules


def import_document(doc_url: str, db, field: str = "General") -> dict:
    doc_id = extract_doc_id(doc_url)
    text = read_doc_text(doc_id)
    comments = read_doc_comments(doc_id)
    lor_type = detect_lor_type(text)

    all_comment_texts = " ".join(c["content"] for c in comments)
    if "[APPROVED]" in all_comment_texts or not comments:
        index_letter(
            doc_id=doc_id,
            text=text,
            lor_type=lor_type,
            field=field,
            approved_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )

    existing_rules = get_rules(db, lor_type)
    new_rules = summarize_comments_to_rules(comments, lor_type, existing_rules)
    if new_rules != existing_rules:
        save_rules(db, lor_type, new_rules)

    return {"doc_id": doc_id, "lor_type": lor_type, "rules_updated": new_rules != existing_rules}
