# LOR Automation System

AI-powered Letter of Recommendation generator for immigration petitions (EB-1A, EB-2 NIW, O-1A).

## Quick Links

| Document | Description |
|----------|-------------|
| [PRD](docs/PRD.md) | Full product requirements |
| [Architecture](docs/ARCHITECTURE.md) | System design + component map |
| [Setup Guide](docs/SETUP.md) | How to deploy the system |
| [Employee Guide](docs/EMPLOYEE_GUIDE.md) | How employees use the sidebar |
| [Team Lead Guide](docs/TEAM_LEAD_GUIDE.md) | How to give feedback that trains the system |
| [Design Spec](docs/superpowers/specs/2026-04-18-lor-automation-design.md) | Technical design spec |

## Stack

- **UI:** Google Docs Sidebar (Apps Script)
- **Backend:** Cloud Run (Python/FastAPI)
- **AI:** AWS Bedrock — Claude Sonnet 4.6
- **Vector DB:** ChromaDB
- **Store:** Firestore
- **Jobs:** Cloud Scheduler

## Folder Structure

```
lor-automation/
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   ├── EMPLOYEE_GUIDE.md
│   ├── TEAM_LEAD_GUIDE.md
│   └── superpowers/specs/
├── src/
│   ├── sidebar/       # Apps Script add-on
│   └── backend/       # Cloud Run FastAPI app
├── scripts/           # Setup + deploy scripts
└── config/            # Settings + pricing constants
```
