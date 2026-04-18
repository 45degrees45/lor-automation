# LOR Automation System — Design Spec

**Date:** 2026-04-18  
**Status:** Approved

---

## Purpose

Build a Google Workspace Add-on that lets employees generate immigration Letters of Recommendation (LOR) using AI (AWS Bedrock Claude Sonnet 4.6). The system self-improves through a feedback loop: team lead comments in Google Docs are ingested weekly to refine writing rules and grow a RAG knowledge base of approved letters.

---

## Architecture

- **UI:** Google Docs sidebar (Apps Script)
- **Backend:** Cloud Run (Python/FastAPI) on GCP project `lor-automation` (new)
- **AI:** AWS Bedrock — Claude Sonnet 4.6 (account 985124898353, ap-south-1)
- **AWS credentials:** stored in GCP Secret Manager
- **Vector DB:** ChromaDB (self-hosted on Cloud Run)
- **Metadata/Rules:** Firestore
- **Cost tracking:** Firestore `token_logs` collection
- **Scheduled jobs:** Cloud Scheduler (weekly feedback ingestion)

---

## Key Flows

### Generation
1. Employee opens sidebar → inputs LOR type + customer doc URL
2. Sidebar calls backend `/generate`
3. Backend reads customer doc → retrieves top-3 RAG examples from ChromaDB → prepends current writing rules → calls Bedrock Claude
4. Draft returned → inserted into Google Doc
5. Token usage + cost logged to Firestore

### Historical Bootstrap (one-time)
1. Admin runs `bulk_import.py` with list of existing approved doc URLs
2. Each doc: text → ChromaDB gold example; comments → Claude summarizes → writing rules
3. Knowledge base pre-seeded on day one

### Feedback Loop (weekly)
1. Cloud Scheduler triggers `/feedback` every Monday
2. Job reads all Google Docs with team lead comments from past 7 days
3. Claude summarizes comment patterns → updates `writing_rules` in Firestore
4. `[APPROVED]` tagged docs added to ChromaDB

---

## Self-Improvement Design (Karpathy-inspired)

- No model fine-tuning — uses prompt engineering + RAG
- Writing rules = Claude's distilled understanding of team lead feedback
- RAG = retrieval of most relevant approved letters at generation time
- Both improve continuously as more letters are approved and commented on

---

## Cost Tracking Schema (Firestore)

```json
{
  "timestamp": "ISO8601",
  "employee_email": "string",
  "doc_id": "string",
  "lor_type": "EB1A | NIW | O1A",
  "input_tokens": "int",
  "output_tokens": "int",
  "cost_usd": "float",
  "model_id": "string"
}
```

---

## Constraints

- Monthly AWS Bedrock cost target: < $15 (well within $33 cap)
- Cloud Run free tier sufficient for < 500 generations/month
- ChromaDB persisted to Cloud Run volume (no external vector DB cost)
- Google Sheets dashboard pulls from Firestore (no extra infra)

---

## Out of Scope (v1)

- Fine-tuning a custom model
- Multi-language LOR support
- Direct USCIS submission
- Mobile interface
