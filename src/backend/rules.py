from datetime import datetime, timezone
from config.settings import FIRESTORE_WRITING_RULES


def get_rules(db, lor_type: str) -> list:
    doc = db.collection(FIRESTORE_WRITING_RULES).document(lor_type).get()
    if doc.exists:
        return doc.to_dict().get("rules", [])
    return []


def save_rules(db, lor_type: str, rules: list) -> None:
    db.collection(FIRESTORE_WRITING_RULES).document(lor_type).set({
        "lor_type": lor_type,
        "rules": rules,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, merge=True)
