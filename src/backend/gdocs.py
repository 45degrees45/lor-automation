import re
import google.auth
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_docs_service():
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
    service = _get_docs_service()
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


def read_doc_comments(doc_id: str) -> list:
    service = _get_drive_service()
    result = service.comments().list(
        fileId=doc_id,
        fields="comments(id,content,resolved,replies)",
        includeDeleted=False
    ).execute()
    return result.get("comments", [])
