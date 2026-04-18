#!/usr/bin/env python3
"""
Creates (or updates) a Google Sheet with all LOR writing guidelines.

Run:
  python scripts/create_reference_sheet.py

Requires:
  - GOOGLE_APPLICATION_CREDENTIALS set, or running with Application Default Credentials
  - Google Sheets API enabled on the GCP project
  - The service account must have Editor access to the target sheet
    (or will create a new sheet and print its URL)

Optional env vars:
  SHEET_ID   — existing sheet to update (if blank, creates a new one)
  SHEET_OWNER_EMAIL — email to share the new sheet with (if creating)
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))

from googleapiclient.discovery import build
import google.auth

# ── Content ──────────────────────────────────────────────────────────────────

BANNED_PHRASES = [
    "critical role", "key role", "pivotal role", "instrumental role",
    "indispensable", "irreplaceable", "unique talent", "exceptional talent",
    "invaluable contribution", "vital contribution",
]

LOR_PILLARS = [
    ("1", "Project Overview",
     "What the project is, its scope, and the petitioner's specific position in it.",
     "Add one sentence explaining what the project does and what the petitioner's specific technical function was — not their job title."),
    ("2", "Organizational Criticality",
     "Why this project was essential to the organization, with concrete stakes.",
     "Why did this organization need this project? What problem went unsolved before it?"),
    ("3", "Significant Contribution",
     "Exactly what the petitioner personally built, designed, or discovered. Use: 'X made a significant contribution by [specific action]...' Never: 'critical role'.",
     "[USCIS FLAG] Replace 'played a critical role' with what they specifically did. Use: 'He/She made a significant contribution by...'"),
    ("4", "Challenges and Solutions",
     "What was technically hard, what prior approaches failed, what the petitioner innovated.",
     "The challenge section is generic. What specifically failed before their approach? What made the solution non-obvious?"),
    ("5", "Success Metrics",
     "Quantified outcomes only. Numbers, percentages, scale, revenue, citations. No adjectives.",
     "Replace all adjectives with numbers. What was the before/after? What is the scale?"),
    ("6", "Devastating Consequence",
     "What would break or regress if this person's contributions were removed.",
     "Add one paragraph on what would be at risk if this person's contributions were removed."),
    ("7", "Distinction from Peers",
     "What makes this person rare in the field — awards, invitations, recognitions.",
     "What distinguishes this person from others at their level? Add specific awards, conference invitations, review panel selections."),
    ("8", "Organization-Wide Impact",
     "How the work spread beyond the immediate team across the organization.",
     "How did this work affect the broader organization? Which other teams adopted it?"),
    ("9", "Industry-Wide Impact",
     "How the work matters to the broader field, not just the employer. Open source, papers, standards.",
     "USCIS requires evidence that extraordinary ability is not limited to a single employer. Add open source, published research, or adoption by other organizations."),
    ("10", "US Benefit",
     "How the petitioner's continued work in the United States serves national interests.",
     "The US benefit paragraph is too generic. Tie to a specific US priority — which US industry benefits?"),
]

OC_PILLARS = [
    ("1", "Recommender Introduction",
     "Establish the recommender's credentials and clarify their professional relationship with the petitioner early. Be specific about how and when they encountered the work.",
     "Clarify relationship in the first paragraph. How did you meet? How long have you known their work?"),
    ("2", "Explain the OC",
     "Describe what the Original Contribution is in clear, accessible language. What does it do? What problem does it solve?",
     "Explain the OC plainly — assume the reviewer is not a technical expert."),
    ("3", "Novelty of the OC",
     "Explain what solutions existed before. What was the state of the art? Be specific about prior approaches.",
     "Name the prior approaches specifically. Vague references to 'traditional methods' are weak."),
    ("4", "Loopholes in Prior Solutions",
     "What were the specific gaps, failures, or limitations in existing approaches? How did those shortcomings affect practitioners?",
     "Be concrete about who was harmed by the old approach and how."),
    ("5", "How the OC Solved Those Issues",
     "Precisely describe how the petitioner's approach addressed each gap. What was the insight that made this possible?",
     "Map each prior gap to a specific feature of the new solution."),
    ("6", "Impact Within the Company",
     "Internal adoption and impact with quantifiable metrics — efficiency gains %, cost savings $, users affected, time saved.",
     "Add specific numbers. Every impact claim needs a metric."),
    ("7", "Major Significance in the Field",
     "How is this OC influencing the broader industry or research community? Citations, adoptions, derivative works, press coverage.",
     "Shift focus outward. Who outside the company knows about and uses this work?"),
    ("8", "Blueprint for the Industry",
     "How other organizations could adopt or adapt this OC. What would they gain? Reference industry trends or government reports if available.",
     "Explain the replicability. Why is this a model others should follow?"),
    ("9", "Forward-Looking US Benefit",
     "How will the petitioner's continued work help the US stay competitive? Connect to US economic, technological, or healthcare security priorities.",
     "This person is not filling a job — they are shaping the future of the field. Make that argument explicitly."),
]

SENIORITY_TONES = [
    ("manager", "Manager / Team Lead",
     "Operational and direct. Close daily observation.",
     "Use: 'I assigned him...', 'I watched her debug...'. Focus on execution quality and technical depth."),
    ("director", "Director",
     "Strategic and cross-functional. Departmental oversight.",
     "Use: 'I oversaw...', 'across the teams I lead...'. Balance technical credibility with organizational impact."),
    ("vp", "VP / SVP",
     "Executive and industry-aware. Company-wide and competitive perspective.",
     "Use: 'In my role overseeing...', 'this shaped our company direction...'. Focus on strategic consequence."),
    ("c_level", "C-Level (CTO/CEO/Chief Scientist)",
     "Authoritative, industry-wide, and visionary.",
     "Use: 'In my decades in this field...', 'this advances the state of the art...'. Connect to mission and industry landscape."),
    ("professor", "Professor / Academic Advisor",
     "Scholarly, field-specific, and comparative.",
     "Compare petitioner to peers in the field. Reference publications, conferences, citations. Establish your own credentials prominently."),
    ("industry_expert", "Independent Industry Expert",
     "Objective, field-wide. Most powerful for EB-1A.",
     "Emphasize independence: 'I became aware of their work through...'. Focus on reputation and field-wide adoption — not employment."),
]

APPROVAL_CHECKLIST = [
    "No banned phrases anywhere in the letter",
    "All pillars addressed with specific facts",
    "Every impact statement has a number",
    "Petitioner's personal contribution clearly separated from team effort",
    "Industry-wide impact goes beyond the current employer",
    "US benefit is specific, not generic",
    "Recommender's credentials and independence established early",
    "No invented facts — everything traceable to the customer intake doc",
]

PROJECT_RESOURCES = [
    # category, resource, purpose, details, monthly_cost
    ("GCP — Infrastructure", "Cloud Run",
     "Hosts the FastAPI backend",
     "Service: lor-backend | Region: asia-south1 | 1GB RAM, 1 CPU, 120s timeout",
     "~$0 (free tier for low volume)"),

    ("GCP — Infrastructure", "Cloud Scheduler",
     "Triggers weekly feedback ingestion job",
     "Job: lor-weekly-feedback | Every Monday 9:00 AM IST | POST /feedback",
     "~$0 (free tier: 3 jobs free)"),

    ("GCP — Storage", "Firestore",
     "Stores token logs, writing rules, doc registry",
     "Collections: token_logs, writing_rules, doc_registry | DB: (default)",
     "~$0 (free tier: 1GB, 50k reads/day)"),

    ("GCP — Security", "Secret Manager",
     "Stores AWS credentials securely",
     "Secret: aws-bedrock-credentials | Accessed by Cloud Run service account",
     "~$0.06/month (1 secret, ~100 accesses)"),

    ("GCP — Identity", "Service Account",
     "Identity used by Cloud Run to access GCP APIs",
     "SA: lor-backend@lor-automation.iam.gserviceaccount.com | Roles: datastore.user, secretmanager.secretAccessor, logging.logWriter",
     "$0"),

    ("GCP — Project", "GCP Project",
     "Container for all GCP resources",
     "Project ID: lor-automation | Billing: linked to existing billing account",
     "$0 (project itself is free)"),

    ("AWS — AI", "AWS Bedrock — Claude Sonnet 4.6",
     "Generates LOR drafts and summarizes feedback into rules",
     "Account: 985124898353 | Region: ap-south-1 | Model: us.anthropic.claude-sonnet-4-6-20250630-v1:0 | $3/1M input, $15/1M output tokens",
     "~$15–25/month at 10 files/day"),

    ("AWS — Security", "AWS IAM User",
     "Grants Cloud Run access to Bedrock",
     "User: claude-code-admin | Policy: AmazonBedrockFullAccess | Key stored in GCP Secret Manager",
     "$0"),

    ("Google — Workspace", "Google Docs API",
     "Reads customer profile docs and team lead comments",
     "Scopes: documents.readonly, drive.readonly | Used by: gdocs.py",
     "$0 (free)"),

    ("Google — Workspace", "Google Sheets API",
     "Populates reference sheet and cost dashboard",
     "Scopes: spreadsheets, drive | Used by: create_reference_sheet.py | Sheet ID: 1v2Kpze5ziDHB82Yl8DwlFE83DDtC3oScp3NTY26GVzA",
     "$0 (free)"),

    ("Google — Workspace", "Google Apps Script Add-on",
     "Employee sidebar inside Google Docs",
     "Files: Code.gs, sidebar.html, appsscript.json | Deployed as Google Workspace Add-on",
     "$0 (free)"),

    ("Vector DB", "ChromaDB",
     "Stores approved LOR letter embeddings for RAG retrieval",
     "Self-hosted on Cloud Run | Persisted to /data/chroma volume | Collection: approved_letters",
     "$0 (self-hosted)"),

    ("Python Package", "FastAPI + Uvicorn",
     "Web framework for Cloud Run backend",
     "fastapi==0.111.0, uvicorn==0.30.1 | Serves /health, /generate, /feedback, /import",
     "$0"),

    ("Python Package", "boto3",
     "AWS SDK — calls Bedrock Claude",
     "boto3==1.34.100 | Used by: aws_auth.py, generator.py, importer.py",
     "$0"),

    ("Python Package", "google-cloud-firestore",
     "Firestore client for token logs and writing rules",
     "google-cloud-firestore==2.16.0 | Used by: tracker.py, rules.py, feedback.py",
     "$0"),

    ("Python Package", "google-cloud-secret-manager",
     "Fetches AWS credentials at runtime",
     "google-cloud-secret-manager==2.20.0 | Used by: aws_auth.py",
     "$0"),

    ("Python Package", "google-api-python-client",
     "Google Docs + Sheets API client",
     "google-api-python-client==2.129.0 | Used by: gdocs.py, create_reference_sheet.py",
     "$0"),

    ("Python Package", "chromadb",
     "Vector database client",
     "chromadb==0.5.0 | Used by: rag.py",
     "$0"),

    ("Python Package", "pydantic",
     "Request/response validation in FastAPI",
     "pydantic==2.7.1 | Used by: main.py",
     "$0"),

    ("Script", "scripts/setup_gcp.sh",
     "One-time GCP project setup",
     "Creates project, enables APIs, creates service account, creates Firestore DB",
     "$0"),

    ("Script", "scripts/deploy.sh",
     "Deploys backend to Cloud Run + creates Cloud Scheduler job",
     "Run after any backend change to redeploy",
     "$0"),

    ("Script", "scripts/bulk_import.py",
     "One-time bootstrap of ChromaDB from existing approved LOR docs",
     "Run: python scripts/bulk_import.py --docs-list docs/historical_doc_urls.txt",
     "$0 + Bedrock cost per doc"),

    ("Script", "scripts/create_reference_sheet.py",
     "Populates this Google Sheet with all writing guidelines",
     "Run: SHEET_ID=... GOOGLE_APPLICATION_CREDENTIALS=... python scripts/create_reference_sheet.py",
     "$0"),

    ("Cost Summary", "Total Estimated Monthly Cost", "",
     "10 files/day × 3 generations avg = ~900 generations/month",
     "~$15–25/month (within $33 AWS cap)"),
]

# ── Sheet builder ─────────────────────────────────────────────────────────────

HEADER_COLOR = {"red": 0.13, "green": 0.34, "blue": 0.62}
SECTION_COLOR = {"red": 0.85, "green": 0.91, "blue": 0.98}
WARN_COLOR = {"red": 1.0, "green": 0.90, "blue": 0.80}


def _cell(value, bold=False, bg=None, wrap=True, size=10):
    fmt = {
        "textFormat": {"bold": bold, "fontSize": size},
        "wrapStrategy": "WRAP" if wrap else "CLIP",
        "verticalAlignment": "TOP",
    }
    if bg:
        fmt["backgroundColor"] = bg
    return {
        "userEnteredValue": {"stringValue": str(value)},
        "userEnteredFormat": fmt,
    }


def _header_row(values, bg=None):
    bg = bg or HEADER_COLOR
    return {"values": [_cell(v, bold=True, bg=bg, size=10) for v in values]}


def _row(values, bg=None):
    return {"values": [_cell(v, bg=bg) for v in values]}


def build_sheet_data():
    """Returns list of (tab_title, rows) tuples."""
    tabs = []

    # ── Tab 1: Standard LOR Pillars ──────────────────────────────────────────
    rows = [
        _header_row(["#", "Pillar", "What to Include", "Team Lead Comment if Missing"],
                    bg=HEADER_COLOR),
    ]
    for num, name, description, comment in LOR_PILLARS:
        rows.append(_row([num, name, description, comment]))
    tabs.append(("Standard LOR Pillars", rows))

    # ── Tab 2: OC Letter Structure ────────────────────────────────────────────
    rows = [
        _header_row(["#", "Section", "What to Write", "Team Lead Comment if Weak"],
                    bg=HEADER_COLOR),
    ]
    for num, name, description, comment in OC_PILLARS:
        rows.append(_row([num, name, description, comment]))
    tabs.append(("OC Letter Structure", rows))

    # ── Tab 3: Banned Phrases ─────────────────────────────────────────────────
    rows = [
        _header_row(["Banned Phrase", "Why Banned", "Replace With"], bg=WARN_COLOR),
        _row(["critical role", "Appears in 90% of weak LORs. USCIS flags as boilerplate.",
              '"made a significant contribution by [specific action]"'], bg=WARN_COLOR),
        _row(["key role", "Same as critical role — vague and overused.",
              '"contributed directly by [what they built/designed/discovered]"']),
        _row(["pivotal role", "No evidence of what they actually did.",
              '"was responsible for [specific deliverable] which resulted in [outcome]"'], bg=WARN_COLOR),
        _row(["instrumental role", "Adjective without substance.",
              '"designed and implemented [X], which [quantified outcome]"']),
        _row(["indispensable", "Claim without proof — replace with the consequence of absence.",
              '"Without their contribution, [system/product] would have [consequence]"'], bg=WARN_COLOR),
        _row(["irreplaceable", "Same as indispensable.",
              '"replacing this work would require [time/cost estimate]"']),
        _row(["invaluable contribution", "The word invaluable signals inability to quantify.",
              '"contribution resulted in [$ amount / % improvement / N users affected]"'], bg=WARN_COLOR),
        _row(["exceptional talent", "Adjective. Prove it with a recognition instead.",
              '"selected as [award/panel/invitation] — one of [N] chosen from [pool size]"']),
    ]
    tabs.append(("Banned Phrases", rows))

    # ── Tab 4: Seniority Tone Guide ───────────────────────────────────────────
    rows = [
        _header_row(["Level Key", "Title", "Voice / Perspective", "Language Guidance"],
                    bg=HEADER_COLOR),
    ]
    for key, title, voice, guidance in SENIORITY_TONES:
        rows.append(_row([key, title, voice, guidance]))
    tabs.append(("Seniority Tone Guide", rows))

    # ── Tab 5: Approval Checklist ─────────────────────────────────────────────
    rows = [
        _header_row(["#", "Checklist Item", "Status (fill in)"], bg=HEADER_COLOR),
    ]
    for i, item in enumerate(APPROVAL_CHECKLIST, 1):
        rows.append(_row([str(i), item, "☐ Pending"]))
    rows.append(_row(["", "", ""]))
    rows.append(_row(["", "To approve: add [APPROVED] as a Google Doc comment.", ""],
                     bg=SECTION_COLOR))
    tabs.append(("Approval Checklist", rows))

    # ── Tab 6: Customer Intake Guide ──────────────────────────────────────────
    rows = [
        _header_row(["Section", "Question to Ask the Customer", "Notes"], bg=HEADER_COLOR),
        _row(["Project Overview", "What is the project, what does it do, and what was your specific role?",
              "Not title — function. What did you actually do day to day?"]),
        _row(["Organizational Criticality", "What would have happened if this project failed or didn't exist?",
              "Stakes. Revenue, users, legal, operational consequences."], bg=SECTION_COLOR),
        _row(["Contribution", "Complete this: 'I personally contributed by ___'",
              "Force specificity. Reject team-level answers."]),
        _row(["Challenges", "What technically failed before your approach? What made your solution non-obvious?",
              "Prior art matters. Name the old approaches."], bg=SECTION_COLOR),
        _row(["Success Metrics", "Give numbers only — no adjectives. Before vs after.",
              "Latency, cost, users, revenue, citations, downloads."]),
        _row(["Devastating Consequence", "What breaks or regresses if you leave tomorrow?",
              "Be honest. Vague answers here are a red flag."], bg=SECTION_COLOR),
        _row(["Distinction", "Awards, recognitions, invitations, selections you've received.",
              "Name specific award + year + pool size if known."]),
        _row(["Org-Wide Impact", "Which other teams or departments used your work?",
              "Internal talks, training, strategy documents that cite your work."], bg=SECTION_COLOR),
        _row(["Industry Impact", "Open source repos, papers, adoptions by other companies.",
              "GitHub URL + stars, paper DOI + citations, company names."]),
        _row(["US Benefit", "What will you build or research next in the US? Which US industry benefits?",
              "Tie to healthcare, AI, infrastructure, economic security."], bg=SECTION_COLOR),
    ]
    tabs.append(("Customer Intake Guide", rows))

    # ── Tab 7: Project Resources ───────────────────────────────────────────────
    COST_COLOR = {"red": 0.85, "green": 0.95, "blue": 0.85}
    rows = [
        _header_row(["Category", "Resource", "Purpose", "Details", "Monthly Cost"],
                    bg=HEADER_COLOR),
    ]
    current_category = None
    for category, resource, purpose, details, cost in PROJECT_RESOURCES:
        is_cost_row = category == "Cost Summary"
        bg = COST_COLOR if is_cost_row else (SECTION_COLOR if category != current_category else None)
        rows.append(_row([category, resource, purpose, details, cost], bg=bg))
        current_category = category
    tabs.append(("Project Resources", rows))

    return tabs


def get_or_create_sheet(service, sheet_id=None, owner_email=None):
    if sheet_id:
        return sheet_id

    spreadsheet = service.spreadsheets().create(body={
        "properties": {"title": "LOR Automation — Writing Reference"},
        "sheets": [{"properties": {"title": "Standard LOR Pillars"}}],
    }).execute()

    sid = spreadsheet["spreadsheetId"]
    url = f"https://docs.google.com/spreadsheets/d/{sid}"
    print(f"✓ Created new sheet: {url}")

    if owner_email:
        drive_service = build("drive", "v3", credentials=service._http.credentials)
        drive_service.permissions().create(
            fileId=sid,
            body={"type": "user", "role": "writer", "emailAddress": owner_email},
        ).execute()
        print(f"✓ Shared with {owner_email}")

    return sid


def populate_sheet(service, sheet_id, tabs_data):
    # Get existing sheet IDs
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"]
                for s in meta["sheets"]}

    requests = []

    # Create missing tabs
    for tab_title, _ in tabs_data:
        if tab_title not in existing:
            requests.append({"addSheet": {"properties": {"title": tab_title}}})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests}
        ).execute()
        # Re-fetch after creating tabs
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existing = {s["properties"]["title"]: s["properties"]["sheetId"]
                    for s in meta["sheets"]}

    # Write data to each tab
    value_ranges = []
    format_requests = []

    for tab_title, rows in tabs_data:
        sid = existing[tab_title]

        # Clear existing content
        format_requests.append({
            "updateCells": {
                "range": {"sheetId": sid},
                "fields": "userEnteredValue,userEnteredFormat",
            }
        })

        # Write rows
        value_ranges.append({
            "updateCells": {
                "range": {"sheetId": sid, "startRowIndex": 0, "startColumnIndex": 0},
                "rows": rows,
                "fields": "userEnteredValue,userEnteredFormat",
            }
        })

        # Auto-resize columns
        format_requests.append({
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sid,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 6,
                }
            }
        })

        # Freeze header row
        format_requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sid,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        })

    # Apply all updates in one batch
    all_requests = format_requests[:1] + value_ranges + format_requests[1:]
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": all_requests}
    ).execute()

    print(f"✓ Populated {len(tabs_data)} tabs")
    print(f"  Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}")


def main():
    sheet_id = os.environ.get("SHEET_ID")
    owner_email = os.environ.get("SHEET_OWNER_EMAIL", "45degreesolutions@gmail.com")

    creds, _ = google.auth.default(scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    service = build("sheets", "v4", credentials=creds)

    sheet_id = get_or_create_sheet(service, sheet_id, owner_email)
    tabs_data = build_sheet_data()
    populate_sheet(service, sheet_id, tabs_data)

    print("\nDone! Tabs created:")
    for title, rows in tabs_data:
        print(f"  • {title} ({len(rows)-1} rows)")


if __name__ == "__main__":
    main()
