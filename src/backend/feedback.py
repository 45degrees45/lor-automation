from datetime import datetime, timezone, timedelta
from gdocs import read_doc_comments, extract_doc_id, read_doc_text
from importer import summarize_comments_to_rules
from rules import get_rules, save_rules
from rag import index_letter

DAYS_LOOKBACK = 7

def run_weekly_feedback(db) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)
    docs = db.collection("doc_registry").where(
        "last_reviewed", ">=", cutoff.isoformat()
    ).stream()

    updated_count = 0
    approved_count = 0

    for doc_snap in docs:
        data = doc_snap.to_dict()
        doc_url = data.get("doc_url")
        lor_type = data.get("lor_type", "EB1A")

        try:
            doc_id = extract_doc_id(doc_url)
            comments = read_doc_comments(doc_id)
            all_text = " ".join(c["content"] for c in comments)

            existing_rules = get_rules(db, lor_type)
            new_rules = summarize_comments_to_rules(comments, lor_type, existing_rules)
            if new_rules != existing_rules:
                save_rules(db, lor_type, new_rules)
                updated_count += 1

            if "[APPROVED]" in all_text:
                text = read_doc_text(doc_id)
                index_letter(
                    doc_id=doc_id,
                    text=text,
                    lor_type=lor_type,
                    field=data.get("field", "General"),
                    approved_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                )
                approved_count += 1

        except Exception as e:
            print(f"Error processing {doc_url}: {e}")

    return {"rules_updated": updated_count, "letters_approved": approved_count}
