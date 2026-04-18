# Setup Instructions

## Prerequisites

- Google Workspace account (admin access to publish add-on)
- AWS account: 985124898353 (Bedrock already enabled)
- GCP billing account
- Claude Code CLI installed

---

## Step 1 — Create GCP Project

Run the setup script (Claude Code will generate this):
```bash
cd /home/jo/claude_projects/lor-automation
bash scripts/setup_gcp.sh
```

This will:
- Create GCP project `lor-automation`
- Enable Cloud Run, Firestore, Secret Manager, Cloud Scheduler APIs
- Create service account `lor-backend@lor-automation.iam.gserviceaccount.com`
- Download credentials JSON

---

## Step 2 — Store AWS Credentials in Secret Manager

Your AWS credentials (for Bedrock) are stored securely in GCP Secret Manager:
```bash
gcloud secrets create aws-bedrock-credentials \
  --data-file=aws_credentials.json \
  --project=lor-automation
```

`aws_credentials.json` format:
```json
{
  "aws_access_key_id": "YOUR_KEY",
  "aws_secret_access_key": "YOUR_SECRET",
  "region_name": "ap-south-1"
}
```

---

## Step 3 — Deploy Backend to Cloud Run

```bash
cd /home/jo/claude_projects/lor-automation
bash scripts/deploy.sh
```

Note the Cloud Run URL output — you'll need it for the sidebar.

---

## Step 4 — Install Google Docs Add-on

1. Open Google Apps Script: https://script.google.com
2. Create new project named `LOR Automation`
3. Copy contents of `sidebar/Code.gs` and `sidebar/sidebar.html`
4. Set `BACKEND_URL` constant to your Cloud Run URL
5. Deploy → New deployment → Add-on
6. Install on your Google Workspace domain

---

## Step 5 — Bootstrap Historical Documents

Run the bulk import to seed the knowledge base with existing approved letters:

```bash
cd /home/jo/claude_projects/lor-automation
python scripts/bulk_import.py --docs-list docs/historical_doc_urls.txt
```

`historical_doc_urls.txt` format (one Google Doc URL per line):
```
https://docs.google.com/document/d/DOC_ID_1/edit
https://docs.google.com/document/d/DOC_ID_2/edit
```

---

## Step 6 — Set Up Weekly Feedback Job

Cloud Scheduler is configured automatically by `setup_gcp.sh`.
It runs every Monday at 9 AM IST and calls `/feedback` on the backend.

---

## Step 7 — Cost Dashboard

1. Open the Google Sheet template (link provided after deploy)
2. It auto-pulls from Firestore token_logs
3. Share with admin/team leads for visibility

---

## Environment Variables (set in Cloud Run)

| Variable | Value |
|----------|-------|
| `GCP_PROJECT` | `lor-automation` |
| `AWS_SECRET_NAME` | `aws-bedrock-credentials` |
| `BEDROCK_MODEL_ID` | `anthropic.claude-sonnet-4-6-20250630-v1:0` |
| `BEDROCK_REGION` | `ap-south-1` |
| `CHROMA_PERSIST_DIR` | `/data/chroma` |
| `FIRESTORE_DB` | `(default)` |
