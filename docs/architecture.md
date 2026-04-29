# LOR Automation — Architecture

This system generates AI-drafted Letters of Recommendation for US immigration petitions (EB-1A, EB-2 NIW, O-1A, OC) by combining a Google Docs sidebar UI with a Cloud Run FastAPI backend that retrieves RAG examples, applies team-lead writing rules, and calls an AI model (AWS Bedrock Claude Sonnet 4.6 by default, with optional Groq / Anthropic / OpenAI / Gemini fallback).

```mermaid
flowchart TD
    subgraph Google Workspace
        A[Customer Google Doc\nPetitioner Profile] -->|URL| B[Employee Google Doc\nDocs Sidebar - Apps Script]
    end

    subgraph Cloud Run - FastAPI Backend
        C[POST /generate] --> D[gdocs.py\nRead customer doc text]
        D --> E[rag.py\nRetrieve similar examples\nfrom ChromaDB]
        D --> F[rules.py\nLoad writing rules\nfrom Firestore]
        E --> G[generator.py\nBuild prompt + call AI]
        F --> G
        G --> H[tracker.py\nLog token usage + cost\nto Firestore]
        H --> I[Return draft LOR]

        J[POST /import] --> K[importer.py\nRead doc + comments\nIndex to ChromaDB\nUpdate writing rules]
        L[POST /feedback] --> M[feedback.py\nWeekly batch:\nre-read comments\nupdate rules + index\napproved letters]
    end

    subgraph AI Providers
        G -->|default| N[AWS Bedrock\nClaude Sonnet 4.6]
        G -->|optional| O[Groq / Anthropic /\nOpenAI / Gemini]
    end

    subgraph GCP - Persistence
        P[(Firestore\ntoken_logs\nwriting_rules\ndoc_registry)]
        Q[(ChromaDB\nCloud Run volume\napproved_letters)]
    end

    subgraph GCP - Ops
        R[Cloud Scheduler] -->|weekly trigger| L
        S[Secret Manager\nAWS credentials]
    end

    B -->|HTTPS POST /generate\nx-api-key header| C
    I -->|Insert draft into doc| B
    F <--> P
    H --> P
    E <--> Q
    K --> Q
    K --> P
    M --> P
    M --> Q
    N <-.->|boto3 InvokeModel| S
```

## Key Components

| Component | Technology | Role |
|-----------|-----------|------|
| Sidebar UI | Apps Script (`sidebar.html`, `Code.gs`) | Employee-facing form; calls `/generate`, inserts draft |
| Backend API | Cloud Run / FastAPI (`main.py`) | Routes: `/generate`, `/import`, `/feedback`, `/stats` |
| Generator | `generator.py` | Builds structured prompt; dispatches to AI provider |
| RAG Store | ChromaDB (`rag.py`) | Cosine-similarity search over approved past letters |
| Writing Rules | Firestore + `rules.py` | Per-LOR-type style rules updated from team-lead comments |
| Importer | `importer.py` | Bulk-loads historical docs into ChromaDB; extracts rules |
| Feedback Loop | `feedback.py` | Weekly Cloud Scheduler job; re-reads comments, improves rules |
| Cost Tracker | `tracker.py` + Firestore | Logs every generation: tokens, model, cost, employee |
| AI — Default | AWS Bedrock Claude Sonnet 4.6 | Primary generation model |
| AI — Optional | Groq / Anthropic / OpenAI / Gemini | Selectable per request via `ai_provider` field |
