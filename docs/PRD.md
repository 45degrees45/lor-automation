# LOR Automation System — Product Requirements Document

**Project:** lor-automation  
**Version:** 1.0  
**Date:** 2026-04-18  
**Owner:** 45degreesolutions@gmail.com

---

## 1. Product Overview

An AI-powered Letter of Recommendation (LOR) generation system built as a **Google Workspace Add-on** (Docs sidebar). Employees use it to draft immigration LORs (EB-1A, EB-2 NIW, O-1A) from customer-submitted Google Docs. The system self-improves by learning from team lead comments on past documents.

---

## 2. Problem Statement

- Employees spend significant time drafting immigration LORs manually
- Quality varies by employee experience
- Team lead feedback is given per letter but never systematically captured
- Existing approved letters and historical feedback are unused assets
- No visibility into AI usage costs per employee or document type

---

## 3. Goals

1. Reduce LOR drafting time by 70%+
2. Improve draft quality using historical approved letters as RAG context
3. Create a continuous self-improvement loop from team lead feedback
4. Track token usage and USD cost per employee and LOR type
5. Bootstrap the system from existing approved documents on day one

---

## 4. Users

| User | Role |
|------|------|
| Employee | Generates LOR drafts using the sidebar |
| Team Lead | Reviews drafts, adds comments in Google Docs |
| Admin | Monitors costs, manages system, runs bulk imports |

---

## 5. LOR Types Supported

| Type | Goal |
|------|------|
| EB-1A | Extraordinary Ability — prove top % globally |
| EB-2 NIW | National Interest Waiver — substantial merit + US benefit |
| O-1A | Extraordinary Ability — temporary visa, sustained acclaim |

---

## 6. Core Features

### F1 — Google Docs Sidebar (Employee UI)
- Select LOR type (EB-1A / NIW / O-1A)
- Link to customer's Google Doc (their profile/docs)
- Generate draft button → inserts draft into current doc
- Sidebar shows token cost for each generation

### F2 — AI Generation Engine
- Backend: Cloud Run (Python/FastAPI)
- Model: AWS Bedrock — Claude Sonnet 4.6 (account: 985124898353, region: ap-south-1)
- RAG: retrieves top-3 most relevant approved letters from ChromaDB
- Applies current writing rules (updated weekly from feedback)

### F3 — Historical Document Import (Bootstrap)
- Admin provides list of existing approved Google Doc URLs
- System reads each doc + all comments via Google Docs API
- Approved text → ChromaDB gold examples
- Comments → Claude summarizes into writing rules
- Tagged by LOR type, field, outcome

### F4 — Feedback Ingestion Pipeline
- Weekly Cloud Scheduler job
- Reads team lead comments from all reviewed docs (past 7 days)
- Claude summarizes patterns → updates writing rules in Firestore
- New approved letters → added to ChromaDB

### F5 — Token & Cost Tracking
- Every Bedrock API call logged to Firestore:
  - timestamp, employee_id, doc_id, lor_type
  - input_tokens, output_tokens, cost_usd, model_id
- Google Sheets dashboard: cost by employee / week / LOR type
- Running monthly total visible to admin

### F6 — Self-Improvement Loop
- Approved letters → ChromaDB (gold examples)
- Team lead comments → writing rules (summarized by Claude)
- RAG pulls relevant examples on every new generation
- Weekly batch refines rules from accumulated feedback

---

## 7. Technical Stack

| Layer | Technology |
|-------|-----------|
| Employee UI | Google Apps Script (Docs sidebar) |
| Backend API | Cloud Run (Python 3.11, FastAPI) |
| AI Model | AWS Bedrock — Claude Sonnet 4.6 |
| AWS Auth | GCP Secret Manager stores AWS credentials |
| Vector DB | ChromaDB (self-hosted on Cloud Run) |
| Metadata/Rules store | Firestore |
| Feedback/Cost dashboard | Google Sheets |
| Scheduled jobs | Cloud Scheduler → Cloud Run |
| GCP Project | lor-automation (new) |
| AWS Account | 985124898353 |

---

## 8. Data Flow

```
Customer Google Doc
       ↓
Employee opens Sidebar → selects LOR type + customer doc URL
       ↓
Sidebar → POST /generate → Cloud Run backend
       ↓
Backend: reads customer doc → RAG from ChromaDB → calls Bedrock Claude
       ↓
Draft inserted into Google Doc + cost logged to Firestore
       ↓
Team Lead adds comments in Google Doc
       ↓
Weekly job: reads comments → Claude summarizes → updates Firestore rules + ChromaDB
```

---

## 9. Self-Improvement Pipeline (Karpathy-inspired)

Inspired by iterative model improvement through feedback loops:

1. **Gold examples** — every approved letter stored in ChromaDB with metadata
2. **Writing rules** — Claude distills team lead comments into explicit rules weekly
3. **RAG at generation time** — top-3 relevant examples retrieved per request
4. **Rule injection** — current writing rules prepended to every system prompt
5. **Compounding improvement** — more letters approved = better RAG = better drafts

---

## 10. Cost Estimate

| Item | Cost |
|------|------|
| AWS Bedrock Claude Sonnet 4.6 | ~$3/1M input tokens, ~$15/1M output tokens |
| Cloud Run | Free tier covers low volume |
| Firestore | Free tier (1GB storage, 50k reads/day) |
| ChromaDB on Cloud Run | $0 (self-hosted) |
| Estimated monthly (100 letters) | ~$3–8/month |

---

## 11. Success Metrics

- Draft generation time < 30 seconds
- Team lead comment rate decreases over time (proxy for quality improvement)
- Monthly cost stays under $15
- 80%+ of drafts require only minor edits after 3 months

---

## 12. Out of Scope (v1)

- Multi-language support
- Direct USCIS submission integration
- Fine-tuning a custom model
- Mobile interface
