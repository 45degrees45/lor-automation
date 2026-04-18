# LOR Automation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-improving Google Docs sidebar that generates immigration LORs (EB-1A, NIW, O-1A) using AWS Bedrock Claude, learning from team lead feedback over time.

**Architecture:** Google Apps Script sidebar → FastAPI backend on Cloud Run → AWS Bedrock Claude Sonnet 4.6. ChromaDB stores approved letters for RAG. Firestore stores writing rules and token cost logs. Cloud Scheduler triggers weekly feedback ingestion.

**Tech Stack:** Python 3.11, FastAPI, boto3, chromadb, google-cloud-firestore, google-auth, Google Apps Script, Cloud Run, Cloud Scheduler, Secret Manager, AWS Bedrock Claude Sonnet 4.6

---

## File Map

```
/home/jo/claude_projects/lor-automation/
├── src/
│   ├── backend/
│   │   ├── main.py              # FastAPI app + route definitions
│   │   ├── generator.py         # Bedrock Claude call + prompt builder
│   │   ├── rag.py               # ChromaDB client: index + retrieve
│   │   ├── rules.py             # Firestore writing rules CRUD
│   │   ├── tracker.py           # Token usage + cost logger (Firestore)
│   │   ├── importer.py          # Bulk import: Google Docs → ChromaDB
│   │   ├── feedback.py          # Weekly job: comments → updated rules
│   │   ├── gdocs.py             # Google Docs API helper (read doc + comments)
│   │   ├── config/
│   │   │   ├── settings.py      # Env vars and constants
│   │   │   └── pricing.py       # Bedrock token pricing per model
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── sidebar/
│       ├── Code.gs              # Apps Script: sidebar logic + backend calls
│       └── sidebar.html         # Sidebar UI: form + cost display
├── scripts/
│   ├── setup_gcp.sh             # Creates GCP project, APIs, service account
│   └── deploy.sh                # Builds + deploys Cloud Run service
└── tests/
    ├── test_generator.py
    ├── test_rag.py
    ├── test_tracker.py
    └── test_feedback.py
```

---

## Task 1: Project Structure + Dependencies

**Files:**
- Create: `src/backend/requirements.txt`
- Create: `src/backend/config/settings.py`
- Create: `src/backend/config/pricing.py`

- [ ] **Step 1: Create requirements.txt**

```
# src/backend/requirements.txt
fastapi==0.111.0
uvicorn==0.30.1
boto3==1.34.100
google-cloud-firestore==2.16.0
google-cloud-secret-manager==2.20.0
google-auth==2.29.0
google-auth-httplib2==0.2.0
google-api-python-client==2.129.0
chromadb==0.5.0
httpx==0.27.0
pydantic==2.7.1
python-dotenv==1.0.1
```

- [ ] **Step 2: Create settings.py**

```python
# src/backend/config/settings.py
import os

GCP_PROJECT = os.environ["GCP_PROJECT"]
AWS_SECRET_NAME = os.environ.get("AWS_SECRET_NAME", "aws-bedrock-credentials")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-sonnet-4-6-20250630-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "/data/chroma")
COLLECTION_NAME = "approved_letters"
FIRESTORE_TOKEN_LOGS = "token_logs"
FIRESTORE_WRITING_RULES = "writing_rules"
FIRESTORE_DOC_REGISTRY = "doc_registry"
```

- [ ] **Step 3: Create pricing.py**

```python
# src/backend/config/pricing.py
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
```

- [ ] **Step 4: Verify structure**

```bash
find /home/jo/claude_projects/lor-automation/src -type f | sort
```

Expected output includes: `settings.py`, `pricing.py`, `requirements.txt`

- [ ] **Step 5: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git init
git add src/backend/requirements.txt src/backend/config/
git commit -m "feat: add backend config and dependencies"
```

---

## Task 2: Token Cost Tracker

**Files:**
- Create: `src/backend/tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_tracker.py
from unittest.mock import MagicMock, patch
from datetime import datetime

def test_log_usage_writes_correct_fields():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    with patch("tracker.firestore.Client", return_value=mock_db):
        from tracker import log_usage
        log_usage(
            db=mock_db,
            employee_email="emp@co.com",
            doc_id="doc123",
            lor_type="EB1A",
            input_tokens=1000,
            output_tokens=500,
            model_id="us.anthropic.claude-sonnet-4-6-20250630-v1:0"
        )

    mock_collection.add.assert_called_once()
    call_args = mock_collection.add.call_args[0][0]
    assert call_args["employee_email"] == "emp@co.com"
    assert call_args["lor_type"] == "EB1A"
    assert call_args["input_tokens"] == 1000
    assert call_args["output_tokens"] == 500
    assert call_args["cost_usd"] == pytest.approx(0.010500, rel=1e-3)
    assert "timestamp" in call_args

def test_calculate_cost_correct():
    from config.pricing import calculate_cost
    cost = calculate_cost(
        "us.anthropic.claude-sonnet-4-6-20250630-v1:0",
        input_tokens=1_000_000,
        output_tokens=0
    )
    assert cost == pytest.approx(3.00)
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_tracker.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'tracker'`

- [ ] **Step 3: Implement tracker.py**

```python
# src/backend/tracker.py
from datetime import datetime, timezone
from google.cloud import firestore
from config.settings import GCP_PROJECT, FIRESTORE_TOKEN_LOGS
from config.pricing import calculate_cost

def log_usage(
    db: firestore.Client,
    employee_email: str,
    doc_id: str,
    lor_type: str,
    input_tokens: int,
    output_tokens: int,
    model_id: str,
) -> None:
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
```

- [ ] **Step 4: Run test — verify PASS**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_tracker.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/tracker.py tests/test_tracker.py
git commit -m "feat: add token cost tracker with Firestore logging"
```

---

## Task 3: AWS Bedrock Credentials Loader

**Files:**
- Create: `src/backend/aws_auth.py`

- [ ] **Step 1: Write the module**

```python
# src/backend/aws_auth.py
import json
import boto3
from google.cloud import secretmanager
from config.settings import GCP_PROJECT, AWS_SECRET_NAME

def get_aws_credentials() -> dict:
    """Fetch AWS credentials from GCP Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{AWS_SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return json.loads(response.payload.data.decode("utf-8"))

def get_bedrock_client():
    """Return a boto3 bedrock-runtime client using credentials from Secret Manager."""
    creds = get_aws_credentials()
    return boto3.client(
        "bedrock-runtime",
        region_name=creds["region_name"],
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
    )
```

- [ ] **Step 2: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/aws_auth.py
git commit -m "feat: fetch AWS credentials from GCP Secret Manager"
```

---

## Task 4: LOR Generator (Bedrock Claude)

**Files:**
- Create: `src/backend/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_generator.py
from unittest.mock import MagicMock, patch
import json

MOCK_RESPONSE = {
    "content": [{"text": "Dear Reviewer, I am writing to support..."}],
    "usage": {"input_tokens": 800, "output_tokens": 600}
}

def test_generate_lor_returns_text_and_tokens():
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps(MOCK_RESPONSE).encode())
    }

    with patch("generator.get_bedrock_client", return_value=mock_client):
        from generator import generate_lor
        result = generate_lor(
            lor_type="EB1A",
            customer_profile="John is a top AI researcher...",
            rag_examples=["Example letter 1", "Example letter 2"],
            writing_rules=["Always quantify impact", "Use 'original contribution' phrasing"],
            recommender_name="Dr. Smith",
            recommender_title="Professor",
            recommender_org="MIT"
        )

    assert "text" in result
    assert result["text"].startswith("Dear")
    assert result["input_tokens"] == 800
    assert result["output_tokens"] == 600

def test_generate_lor_prompt_includes_lor_type():
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps(MOCK_RESPONSE).encode())
    }

    with patch("generator.get_bedrock_client", return_value=mock_client):
        from generator import generate_lor, build_prompt
        prompt = build_prompt(
            lor_type="NIW",
            customer_profile="Jane works in healthcare...",
            rag_examples=[],
            writing_rules=[],
            recommender_name="Dr. Lee",
            recommender_title="Director",
            recommender_org="Johns Hopkins"
        )

    assert "NIW" in prompt or "National Interest Waiver" in prompt
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_generator.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'generator'`

- [ ] **Step 3: Implement generator.py**

```python
# src/backend/generator.py
import json
import boto3
from aws_auth import get_bedrock_client
from config.settings import BEDROCK_MODEL_ID

LOR_DESCRIPTIONS = {
    "EB1A": "EB-1A Extraordinary Ability (prove top percentage globally)",
    "NIW": "EB-2 National Interest Waiver (substantial merit + US national benefit)",
    "O1A": "O-1A Extraordinary Ability temporary visa (sustained acclaim + critical role)",
}

def build_prompt(
    lor_type: str,
    customer_profile: str,
    rag_examples: list[str],
    writing_rules: list[str],
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
) -> str:
    examples_block = "\n\n---\n\n".join(rag_examples) if rag_examples else "None available."
    rules_block = "\n".join(f"- {r}" for r in writing_rules) if writing_rules else "None yet."

    return f"""You are an expert immigration attorney drafting a Letter of Recommendation.

LETTER TYPE: {LOR_DESCRIPTIONS.get(lor_type, lor_type)}

WRITING RULES (follow these strictly):
{rules_block}

APPROVED EXAMPLE LETTERS (use as style and structure reference):
{examples_block}

RECOMMENDER:
Name: {recommender_name}
Title: {recommender_title}
Organization: {recommender_org}

PETITIONER PROFILE:
{customer_profile}

Write a complete, professional Letter of Recommendation. Start directly with the date line. Do not include any commentary or explanation outside the letter itself."""

def generate_lor(
    lor_type: str,
    customer_profile: str,
    rag_examples: list[str],
    writing_rules: list[str],
    recommender_name: str,
    recommender_title: str,
    recommender_org: str,
) -> dict:
    client = get_bedrock_client()
    prompt = build_prompt(
        lor_type, customer_profile, rag_examples,
        writing_rules, recommender_name, recommender_title, recommender_org
    )

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    })

    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    result = json.loads(response["body"].read())

    return {
        "text": result["content"][0]["text"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
    }
```

- [ ] **Step 4: Run test — verify PASS**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_generator.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/generator.py tests/test_generator.py
git commit -m "feat: LOR generator using AWS Bedrock Claude"
```

---

## Task 5: ChromaDB RAG Module

**Files:**
- Create: `src/backend/rag.py`
- Create: `tests/test_rag.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rag.py
from unittest.mock import MagicMock, patch

def test_index_letter_adds_to_collection():
    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("rag.chromadb.PersistentClient", return_value=mock_client):
        from rag import index_letter
        index_letter(
            doc_id="doc123",
            text="This is an approved EB-1A letter...",
            lor_type="EB1A",
            field="AI",
            approved_date="2026-04-01"
        )

    mock_collection.add.assert_called_once()
    call_kwargs = mock_collection.add.call_args[1]
    assert "doc123" in call_kwargs["ids"]
    assert call_kwargs["metadatas"][0]["lor_type"] == "EB1A"

def test_retrieve_examples_returns_texts():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Letter A text", "Letter B text", "Letter C text"]]
    }
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("rag.chromadb.PersistentClient", return_value=mock_client):
        from rag import retrieve_examples
        results = retrieve_examples(query="AI researcher extraordinary ability", lor_type="EB1A", n=3)

    assert len(results) == 3
    assert results[0] == "Letter A text"
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_rag.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'rag'`

- [ ] **Step 3: Implement rag.py**

```python
# src/backend/rag.py
import chromadb
from config.settings import CHROMA_PERSIST_DIR, COLLECTION_NAME

def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

def index_letter(
    doc_id: str,
    text: str,
    lor_type: str,
    field: str,
    approved_date: str,
) -> None:
    collection = _get_collection()
    collection.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[{
            "lor_type": lor_type,
            "field": field,
            "approved_date": approved_date,
        }]
    )

def retrieve_examples(query: str, lor_type: str, n: int = 3) -> list[str]:
    collection = _get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n,
        where={"lor_type": lor_type} if lor_type else None,
    )
    return results["documents"][0] if results["documents"] else []
```

- [ ] **Step 4: Run test — verify PASS**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
python -m pytest ../../tests/test_rag.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/rag.py tests/test_rag.py
git commit -m "feat: ChromaDB RAG module for approved letter retrieval"
```

---

## Task 6: Writing Rules (Firestore CRUD)

**Files:**
- Create: `src/backend/rules.py`

- [ ] **Step 1: Implement rules.py**

```python
# src/backend/rules.py
from google.cloud import firestore
from config.settings import FIRESTORE_WRITING_RULES

def get_rules(db: firestore.Client, lor_type: str) -> list[str]:
    doc = db.collection(FIRESTORE_WRITING_RULES).document(lor_type).get()
    if doc.exists:
        return doc.to_dict().get("rules", [])
    return []

def save_rules(db: firestore.Client, lor_type: str, rules: list[str]) -> None:
    from datetime import datetime, timezone
    db.collection(FIRESTORE_WRITING_RULES).document(lor_type).set({
        "lor_type": lor_type,
        "rules": rules,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, merge=True)
```

- [ ] **Step 2: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/rules.py
git commit -m "feat: writing rules CRUD via Firestore"
```

---

## Task 7: Google Docs API Helper

**Files:**
- Create: `src/backend/gdocs.py`

- [ ] **Step 1: Implement gdocs.py**

```python
# src/backend/gdocs.py
import re
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

def _get_service():
    # In Cloud Run, uses Application Default Credentials (service account)
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("docs", "v1", credentials=creds)

def _get_drive_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def extract_doc_id(url: str) -> str:
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract doc ID from URL: {url}")
    return match.group(1)

def read_doc_text(doc_id: str) -> str:
    service = _get_service()
    doc = service.documents().get(documentId=doc_id).execute()
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if paragraph:
            for run in paragraph.get("elements", []):
                text_run = run.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))
    return "".join(text_parts).strip()

def read_doc_comments(doc_id: str) -> list[dict]:
    service = _get_drive_service()
    result = service.comments().list(
        fileId=doc_id,
        fields="comments(id,content,resolved,replies)",
        includeDeleted=False
    ).execute()
    return result.get("comments", [])
```

- [ ] **Step 2: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/gdocs.py
git commit -m "feat: Google Docs API helper for reading text and comments"
```

---

## Task 8: FastAPI Backend + /generate Endpoint

**Files:**
- Create: `src/backend/main.py`

- [ ] **Step 1: Implement main.py**

```python
# src/backend/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

from generator import generate_lor
from rag import retrieve_examples
from rules import get_rules
from tracker import log_usage
from gdocs import read_doc_text, extract_doc_id

app = FastAPI(title="LOR Automation API")
db = firestore.Client()

class GenerateRequest(BaseModel):
    lor_type: str          # EB1A | NIW | O1A
    customer_doc_url: str
    recommender_name: str
    recommender_title: str
    recommender_org: str
    employee_email: str

class GenerateResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        doc_id = extract_doc_id(req.customer_doc_url)
        customer_profile = read_doc_text(doc_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read customer doc: {e}")

    rag_examples = retrieve_examples(
        query=customer_profile[:500],
        lor_type=req.lor_type,
        n=3
    )
    writing_rules = get_rules(db, req.lor_type)

    result = generate_lor(
        lor_type=req.lor_type,
        customer_profile=customer_profile,
        rag_examples=rag_examples,
        writing_rules=writing_rules,
        recommender_name=req.recommender_name,
        recommender_title=req.recommender_title,
        recommender_org=req.recommender_org,
    )

    log_usage(
        db=db,
        employee_email=req.employee_email,
        doc_id=doc_id,
        lor_type=req.lor_type,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        model_id=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6-20250630-v1:0"),
    )

    from config.pricing import calculate_cost
    cost = calculate_cost(
        os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6-20250630-v1:0"),
        result["input_tokens"],
        result["output_tokens"]
    )

    return GenerateResponse(
        text=result["text"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cost_usd=cost,
    )
```

- [ ] **Step 2: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/main.py
git commit -m "feat: FastAPI /generate endpoint wiring RAG + Bedrock + cost tracker"
```

---

## Task 9: Historical Bulk Import

**Files:**
- Create: `src/backend/importer.py`

- [ ] **Step 1: Implement importer.py**

```python
# src/backend/importer.py
import json
from google.cloud import firestore
from gdocs import read_doc_text, read_doc_comments, extract_doc_id
from rag import index_letter
from rules import get_rules, save_rules
from generator import generate_lor
import boto3
from aws_auth import get_bedrock_client
from config.settings import BEDROCK_MODEL_ID, GCP_PROJECT
import re
from datetime import datetime, timezone

def detect_lor_type(text: str) -> str:
    text_upper = text.upper()
    if "EB-1A" in text_upper or "EB1A" in text_upper:
        return "EB1A"
    if "NIW" in text_upper or "NATIONAL INTEREST" in text_upper:
        return "NIW"
    if "O-1A" in text_upper or "O1A" in text_upper:
        return "O1A"
    return "EB1A"  # default

def summarize_comments_to_rules(comments: list[dict], lor_type: str, existing_rules: list[str]) -> list[str]:
    """Ask Claude to distill comments into writing rules."""
    comment_texts = [c["content"] for c in comments if not c.get("resolved")]
    if not comment_texts:
        return existing_rules

    client = get_bedrock_client()
    import json as _json

    prompt = f"""You are analyzing team lead feedback comments on immigration LOR drafts ({lor_type} type).

Existing writing rules:
{chr(10).join(f"- {r}" for r in existing_rules) or "None yet."}

New comments from team lead:
{chr(10).join(f"- {c}" for c in comment_texts)}

Produce an updated list of 5-15 clear, actionable writing rules for {lor_type} letters.
Merge new insights with existing rules. Remove duplicates. Be specific and concrete.
Return ONLY a JSON array of strings, no other text.
Example: ["Rule 1", "Rule 2"]"""

    body = _json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    result = _json.loads(response["body"].read())
    text = result["content"][0]["text"].strip()

    try:
        return _json.loads(text)
    except Exception:
        return existing_rules

def import_document(doc_url: str, db: firestore.Client, field: str = "General") -> dict:
    doc_id = extract_doc_id(doc_url)
    text = read_doc_text(doc_id)
    comments = read_doc_comments(doc_id)
    lor_type = detect_lor_type(text)

    # Check if [APPROVED] tag present — if so, index as gold example
    all_comment_texts = " ".join(c["content"] for c in comments)
    if "[APPROVED]" in all_comment_texts or not comments:
        index_letter(
            doc_id=doc_id,
            text=text,
            lor_type=lor_type,
            field=field,
            approved_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )

    # Update writing rules from comments
    existing_rules = get_rules(db, lor_type)
    new_rules = summarize_comments_to_rules(comments, lor_type, existing_rules)
    if new_rules != existing_rules:
        save_rules(db, lor_type, new_rules)

    return {"doc_id": doc_id, "lor_type": lor_type, "rules_updated": new_rules != existing_rules}
```

- [ ] **Step 2: Create bulk_import CLI script**

```python
# scripts/bulk_import.py
#!/usr/bin/env python3
"""
Run: python scripts/bulk_import.py --docs-list docs/historical_doc_urls.txt
Each line in the file should be a Google Doc URL.
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))

from google.cloud import firestore
from importer import import_document

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-list", required=True, help="Path to file with one Google Doc URL per line")
    parser.add_argument("--field", default="General", help="Professional field (e.g., AI, Healthcare)")
    args = parser.parse_args()

    db = firestore.Client()

    with open(args.docs_list) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Importing {len(urls)} documents...")
    for i, url in enumerate(urls, 1):
        try:
            result = import_document(url, db, field=args.field)
            print(f"[{i}/{len(urls)}] ✓ {result['doc_id']} ({result['lor_type']})")
        except Exception as e:
            print(f"[{i}/{len(urls)}] ✗ FAILED: {url} — {e}")

    print("Done.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/importer.py scripts/bulk_import.py
git commit -m "feat: bulk historical document import + rule bootstrapping"
```

---

## Task 10: Weekly Feedback Ingestion Job

**Files:**
- Create: `src/backend/feedback.py`

- [ ] **Step 1: Implement feedback.py**

```python
# src/backend/feedback.py
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from gdocs import read_doc_comments, extract_doc_id
from importer import summarize_comments_to_rules
from rules import get_rules, save_rules
from rag import index_letter

DAYS_LOOKBACK = 7

def run_weekly_feedback(db: firestore.Client) -> dict:
    """
    Called by /feedback endpoint (triggered by Cloud Scheduler weekly).
    Reads doc_registry to find docs reviewed in the past 7 days.
    Updates writing rules and indexes newly approved letters.
    """
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
                from gdocs import read_doc_text
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
```

- [ ] **Step 2: Add /feedback route to main.py**

Add this to `src/backend/main.py` after the `/generate` route:

```python
@app.post("/feedback")
def trigger_feedback():
    from feedback import run_weekly_feedback
    result = run_weekly_feedback(db)
    return result
```

Also add a `/import` route for the bulk import endpoint:

```python
class ImportRequest(BaseModel):
    doc_url: str
    field: str = "General"

@app.post("/import")
def import_doc(req: ImportRequest):
    from importer import import_document
    result = import_document(req.doc_url, db, field=req.field)
    return result
```

- [ ] **Step 3: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/feedback.py src/backend/main.py
git commit -m "feat: weekly feedback ingestion job + /feedback and /import endpoints"
```

---

## Task 11: Dockerfile + Cloud Run Deployment

**Files:**
- Create: `src/backend/Dockerfile`
- Create: `scripts/setup_gcp.sh`
- Create: `scripts/deploy.sh`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# src/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ChromaDB persistence directory
RUN mkdir -p /data/chroma

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Create setup_gcp.sh**

```bash
#!/bin/bash
# scripts/setup_gcp.sh
set -e

PROJECT_ID="lor-automation"
REGION="asia-south1"
SA_NAME="lor-backend"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating GCP project..."
gcloud projects create $PROJECT_ID --name="LOR Automation" || echo "Project may already exist"
gcloud config set project $PROJECT_ID

echo "Enabling billing (manual step required if not done)..."
echo "Go to: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
read -p "Press enter once billing is enabled..."

echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  docs.googleapis.com \
  drive.googleapis.com \
  --project=$PROJECT_ID

echo "Creating service account..."
gcloud iam service-accounts create $SA_NAME \
  --display-name="LOR Backend" \
  --project=$PROJECT_ID || echo "SA may already exist"

echo "Granting roles..."
for ROLE in \
  roles/datastore.user \
  roles/secretmanager.secretAccessor \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE"
done

echo "Creating Firestore database..."
gcloud firestore databases create --location=$REGION --project=$PROJECT_ID || echo "Firestore may already exist"

echo ""
echo "✓ Setup complete."
echo ""
echo "Next: add your AWS credentials as a secret:"
echo "  gcloud secrets create aws-bedrock-credentials --project=$PROJECT_ID"
echo "  gcloud secrets versions add aws-bedrock-credentials --data-file=aws_credentials.json"
```

- [ ] **Step 3: Create deploy.sh**

```bash
#!/bin/bash
# scripts/deploy.sh
set -e

PROJECT_ID="lor-automation"
REGION="asia-south1"
SERVICE_NAME="lor-backend"
SA_EMAIL="lor-backend@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source src/backend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --service-account=$SA_EMAIL \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},BEDROCK_REGION=ap-south-1,BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250630-v1:0" \
  --memory=1Gi \
  --cpu=1 \
  --timeout=120 \
  --no-allow-unauthenticated \
  --mount-volumes=name=chroma-vol,type=memory \
  --volume-mounts=chroma-vol:/data/chroma

echo ""
URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
echo "✓ Deployed: $URL"
echo ""
echo "Set up weekly Cloud Scheduler job:"
gcloud scheduler jobs create http lor-weekly-feedback \
  --schedule="0 9 * * 1" \
  --time-zone="Asia/Kolkata" \
  --uri="${URL}/feedback" \
  --http-method=POST \
  --oidc-service-account-email=$SA_EMAIL \
  --location=$REGION \
  --project=$PROJECT_ID || echo "Scheduler job may already exist"

echo "✓ Done. Backend URL: $URL"
echo "Copy this URL into the sidebar Code.gs BACKEND_URL constant."
```

- [ ] **Step 4: Make scripts executable**

```bash
chmod +x /home/jo/claude_projects/lor-automation/scripts/setup_gcp.sh
chmod +x /home/jo/claude_projects/lor-automation/scripts/deploy.sh
```

- [ ] **Step 5: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/backend/Dockerfile scripts/
git commit -m "feat: Dockerfile + GCP setup and Cloud Run deploy scripts"
```

---

## Task 12: Google Docs Sidebar (Apps Script)

**Files:**
- Create: `src/sidebar/Code.gs`
- Create: `src/sidebar/sidebar.html`

- [ ] **Step 1: Create Code.gs**

```javascript
// src/sidebar/Code.gs
const BACKEND_URL = "https://YOUR-CLOUD-RUN-URL"; // Replace after deploy

function onOpen() {
  DocumentApp.getUi()
    .createAddonMenu()
    .addItem("Open LOR Generator", "showSidebar")
    .addToUi();
}

function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile("sidebar")
    .setTitle("LOR Generator")
    .setWidth(320);
  DocumentApp.getUi().showSidebar(html);
}

function generateLOR(formData) {
  const doc = DocumentApp.getActiveDocument();
  const employeeEmail = Session.getActiveUser().getEmail();

  const payload = {
    lor_type: formData.lorType,
    customer_doc_url: formData.customerDocUrl,
    recommender_name: formData.recommenderName,
    recommender_title: formData.recommenderTitle,
    recommender_org: formData.recommenderOrg,
    employee_email: employeeEmail,
  };

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    headers: {
      Authorization: "Bearer " + ScriptApp.getIdentityToken(),
    },
    muteHttpExceptions: true,
  };

  const response = UrlFetchApp.fetch(BACKEND_URL + "/generate", options);
  const code = response.getResponseCode();

  if (code !== 200) {
    throw new Error("Backend error " + code + ": " + response.getContentText());
  }

  const result = JSON.parse(response.getContentText());

  // Insert draft at end of document
  const body = doc.getBody();
  body.appendPageBreak();
  body.appendParagraph("--- GENERATED DRAFT ---").setHeading(DocumentApp.ParagraphHeading.HEADING2);
  body.appendParagraph(result.text);

  return {
    inputTokens: result.input_tokens,
    outputTokens: result.output_tokens,
    costUsd: result.cost_usd,
  };
}
```

- [ ] **Step 2: Create sidebar.html**

```html
<!-- src/sidebar/sidebar.html -->
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <style>
    body { font-family: Arial, sans-serif; font-size: 13px; padding: 12px; }
    label { display: block; font-weight: bold; margin-top: 10px; margin-bottom: 3px; }
    select, input { width: 100%; padding: 6px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 3px; }
    button { width: 100%; margin-top: 14px; padding: 10px; background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
    button:disabled { background: #aaa; }
    #status { margin-top: 10px; color: #555; font-size: 12px; }
    #cost { margin-top: 8px; padding: 8px; background: #f0f7ff; border-radius: 4px; font-size: 12px; display: none; }
    .error { color: #d32f2f; }
  </style>
</head>
<body>
  <h3 style="margin-top:0">LOR Generator</h3>

  <label>LOR Type</label>
  <select id="lorType">
    <option value="EB1A">EB-1A — Extraordinary Ability</option>
    <option value="NIW">EB-2 NIW — National Interest Waiver</option>
    <option value="O1A">O-1A — Extraordinary Ability (Temp)</option>
  </select>

  <label>Customer Google Doc URL</label>
  <input type="url" id="customerDocUrl" placeholder="https://docs.google.com/document/d/...">

  <label>Recommender Name</label>
  <input type="text" id="recommenderName" placeholder="Dr. Jane Smith">

  <label>Recommender Title</label>
  <input type="text" id="recommenderTitle" placeholder="Professor of Computer Science">

  <label>Recommender Organization</label>
  <input type="text" id="recommenderOrg" placeholder="MIT">

  <button id="generateBtn" onclick="generate()">Generate Letter</button>

  <div id="status"></div>
  <div id="cost"></div>

  <script>
    function generate() {
      const btn = document.getElementById("generateBtn");
      const status = document.getElementById("status");
      const costDiv = document.getElementById("cost");

      const formData = {
        lorType: document.getElementById("lorType").value,
        customerDocUrl: document.getElementById("customerDocUrl").value.trim(),
        recommenderName: document.getElementById("recommenderName").value.trim(),
        recommenderTitle: document.getElementById("recommenderTitle").value.trim(),
        recommenderOrg: document.getElementById("recommenderOrg").value.trim(),
      };

      if (!formData.customerDocUrl || !formData.recommenderName) {
        status.innerHTML = '<span class="error">Please fill all fields.</span>';
        return;
      }

      btn.disabled = true;
      btn.textContent = "Generating...";
      status.textContent = "Calling AI model... this takes ~20 seconds.";
      costDiv.style.display = "none";

      google.script.run
        .withSuccessHandler(function(result) {
          btn.disabled = false;
          btn.textContent = "Generate Letter";
          status.textContent = "✓ Draft inserted at end of document.";
          costDiv.style.display = "block";
          costDiv.innerHTML =
            "Tokens: " + result.inputTokens + " in / " + result.outputTokens + " out<br>" +
            "Cost: $" + result.costUsd.toFixed(4);
        })
        .withFailureHandler(function(err) {
          btn.disabled = false;
          btn.textContent = "Generate Letter";
          status.innerHTML = '<span class="error">Error: ' + err.message + '</span>';
        })
        .generateLOR(formData);
    }
  </script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/sidebar/
git commit -m "feat: Google Docs sidebar for LOR generation"
```

---

## Task 13: End-to-End Smoke Test

- [ ] **Step 1: Run all unit tests**

```bash
cd /home/jo/claude_projects/lor-automation/src/backend
pip install -r requirements.txt
python -m pytest ../../tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Run GCP setup**

```bash
cd /home/jo/claude_projects/lor-automation
bash scripts/setup_gcp.sh
```

- [ ] **Step 3: Add AWS credentials to Secret Manager**

Create `aws_credentials.json` (do NOT commit this file):
```json
{
  "aws_access_key_id": "YOUR_IAM_KEY",
  "aws_secret_access_key": "YOUR_IAM_SECRET",
  "region_name": "ap-south-1"
}
```

Then:
```bash
gcloud secrets create aws-bedrock-credentials --project=lor-automation
gcloud secrets versions add aws-bedrock-credentials --data-file=aws_credentials.json
rm aws_credentials.json
```

- [ ] **Step 4: Deploy to Cloud Run**

```bash
bash scripts/deploy.sh
```

Note the URL printed at the end. Copy it.

- [ ] **Step 5: Test /health endpoint**

```bash
curl $(gcloud run services describe lor-backend --region=asia-south1 --project=lor-automation --format="value(status.url)")/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 6: Update sidebar BACKEND_URL**

In `src/sidebar/Code.gs`, replace `YOUR-CLOUD-RUN-URL` with the actual Cloud Run URL.

- [ ] **Step 7: Install sidebar in Google Docs**
1. Go to https://script.google.com → New project
2. Paste contents of `Code.gs` and `sidebar.html`
3. Deploy → Test deployments → Install as add-on
4. Open any Google Doc → Extensions → LOR Generator → Open Sidebar

- [ ] **Step 8: Final commit**

```bash
cd /home/jo/claude_projects/lor-automation
git add src/sidebar/Code.gs
git commit -m "feat: update sidebar with production backend URL"
```
