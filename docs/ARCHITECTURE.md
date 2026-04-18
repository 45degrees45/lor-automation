# System Architecture

## Component Map

```
┌─────────────────────────────────────────────────────┐
│                  GOOGLE WORKSPACE                    │
│                                                      │
│  Customer Google Doc ──→ Employee Google Doc         │
│                               │                      │
│                          Docs Sidebar                │
│                         (Apps Script)                │
└───────────────────────────────┼─────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────┐
│                    GCP — lor-automation              │
│                                                      │
│  Cloud Run: FastAPI Backend                          │
│  ├── /generate  (draft LOR)                          │
│  ├── /import    (bulk historical docs)               │
│  └── /feedback  (trigger weekly batch)               │
│                                                      │
│  Cloud Scheduler ──→ Weekly feedback job             │
│                                                      │
│  Firestore                                           │
│  ├── token_logs (cost tracking)                      │
│  ├── writing_rules (current LOR rules)               │
│  └── doc_registry (tracked docs)                     │
│                                                      │
│  ChromaDB (Cloud Run volume)                         │
│  └── approved_letters collection                     │
│                                                      │
│  Secret Manager                                      │
│  └── aws-bedrock-credentials                         │
└───────────────────────────────┬─────────────────────┘
                                │ boto3
                                ▼
┌─────────────────────────────────────────────────────┐
│               AWS — 985124898353 (ap-south-1)        │
│                                                      │
│  Bedrock: Claude Sonnet 4.6                          │
│  (claude-sonnet-4-6 via InvokeModel API)             │
└─────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. `sidebar/` — Apps Script Google Docs Add-on
- `sidebar.html` — UI: LOR type selector, customer doc input, generate button, cost display
- `Code.gs` — calls backend /generate, inserts draft into doc

### 2. `backend/` — Cloud Run FastAPI app
- `main.py` — FastAPI app, route definitions
- `generator.py` — builds prompt, calls Bedrock, returns draft
- `rag.py` — ChromaDB client, retrieves relevant examples
- `rules.py` — loads/saves writing rules from Firestore
- `tracker.py` — logs token usage + cost to Firestore
- `importer.py` — bulk import: reads Google Docs + comments, indexes to ChromaDB
- `feedback.py` — weekly job: reads new comments, updates rules via Claude

### 3. `config/` — Configuration
- `settings.py` — env vars, model IDs, GCP/AWS config
- `pricing.py` — Bedrock token pricing constants

### 4. `scripts/` — Operational scripts
- `setup_gcp.sh` — creates GCP project, enables APIs, creates service account
- `bulk_import.py` — CLI to run historical doc import
- `deploy.sh` — deploys Cloud Run backend

## Data Schemas

### Firestore: `token_logs`
```json
{
  "id": "auto",
  "timestamp": "2026-04-18T10:30:00Z",
  "employee_email": "employee@company.com",
  "doc_id": "google_doc_id",
  "lor_type": "EB1A",
  "input_tokens": 1240,
  "output_tokens": 820,
  "cost_usd": 0.016,
  "model_id": "claude-sonnet-4-6"
}
```

### Firestore: `writing_rules`
```json
{
  "lor_type": "EB1A",
  "version": 12,
  "updated_at": "2026-04-14T00:00:00Z",
  "rules": [
    "Always quantify impact with specific metrics",
    "Use 'original contribution of major significance' phrasing",
    "Recommender must establish independence from petitioner early"
  ]
}
```

### ChromaDB: `approved_letters` collection
```
document: full letter text
metadata: {
  lor_type, field, outcome, doc_id,
  approved_date, recommender_title
}
embedding: text-embedding-3 via Bedrock
```
