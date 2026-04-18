"""Tests for main.py FastAPI endpoints."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub external packages not installed in this test environment.
# Injected into sys.modules BEFORE any backend module is imported, so that
# import-time code (google.auth.default, etc.) doesn't fail.
# These are narrow stubs — they don't replace the top-level `google` package,
# which would break google.protobuf (used by chromadb).
# ---------------------------------------------------------------------------

def _stub(name):
    if name not in sys.modules:
        sys.modules[name] = MagicMock()

_stub("google.auth")
_stub("google.auth.transport")
_stub("google.auth.transport.requests")
_stub("google.oauth2")
_stub("google.oauth2.credentials")
_stub("googleapiclient")
_stub("googleapiclient.discovery")

# google.cloud.firestore: inject mock so `from google.cloud import firestore`
# and `firestore.Client()` both work without real GCP credentials.
_mock_firestore = MagicMock()
_mock_db = MagicMock()
_mock_firestore.Client.return_value = _mock_db

# Preserve the real google.cloud if it already exists (chromadb imports it);
# only inject the firestore sub-module.
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.firestore"] = _mock_firestore

# ---------------------------------------------------------------------------
# Import main (with firestore stub live).  We must also stub all collaborators
# during this import so that generator / rag / gdocs / tracker are importable
# even if their own transitive deps (boto3, chromadb, google-api) are absent.
# We start these patches, import main, then STOP them — each test re-applies
# them via the `mocks` fixture so we don't pollute other test modules.
# ---------------------------------------------------------------------------

_TARGETS = [
    "generator.generate_lor",
    "rag.retrieve_examples",
    "rules.get_rules",
    "tracker.log_usage",
    "gdocs.read_doc_text",
    "gdocs.extract_doc_id",
]

_boot_patchers = [patch(t, MagicMock()) for t in _TARGETS]
for _p in _boot_patchers:
    _p.start()

import main  # noqa: E402
from main import app  # noqa: E402

for _p in _boot_patchers:
    _p.stop()

# The names that matter at runtime are those imported into main's namespace:
_MAIN_TARGETS = [
    "main.generate_lor",
    "main.retrieve_examples",
    "main.get_rules",
    "main.log_usage",
    "main.read_doc_text",
    "main.extract_doc_id",
]

from fastapi.testclient import TestClient  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mocks():
    """Start fresh mocks for each test and stop them afterwards."""
    m = {
        "generate_lor": MagicMock(return_value={
            "text": "Dear Sir/Madam, ...",
            "input_tokens": 1000,
            "output_tokens": 500,
        }),
        "retrieve_examples": MagicMock(return_value=["example 1", "example 2"]),
        "get_rules": MagicMock(return_value=["Rule A", "Rule B"]),
        "log_usage": MagicMock(return_value=0.0105),
        "read_doc_text": MagicMock(return_value="Customer profile text."),
        "extract_doc_id": MagicMock(return_value="DOC_ID_123"),
    }
    patchers = [
        patch("main.generate_lor", m["generate_lor"]),
        patch("main.retrieve_examples", m["retrieve_examples"]),
        patch("main.get_rules", m["get_rules"]),
        patch("main.log_usage", m["log_usage"]),
        patch("main.read_doc_text", m["read_doc_text"]),
        patch("main.extract_doc_id", m["extract_doc_id"]),
    ]
    for p in patchers:
        p.start()
    yield m
    for p in patchers:
        p.stop()


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared payload
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "lor_type": "EB1A",
    "customer_doc_url": "https://docs.google.com/document/d/DOC_ID_123/edit",
    "recommender_name": "Dr. Jane Smith",
    "recommender_title": "Professor",
    "recommender_org": "MIT",
    "employee_email": "employee@example.com",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestGenerateEndpoint:
    def test_generate_valid_input_returns_200(self, client, mocks):
        response = client.post("/generate", json=VALID_PAYLOAD)
        assert response.status_code == 200

    def test_generate_response_has_required_fields(self, client, mocks):
        response = client.post("/generate", json=VALID_PAYLOAD)
        data = response.json()
        assert "text" in data
        assert "input_tokens" in data
        assert "output_tokens" in data
        assert "cost_usd" in data

    def test_generate_response_values(self, client, mocks):
        response = client.post("/generate", json=VALID_PAYLOAD)
        data = response.json()
        assert data["text"] == "Dear Sir/Madam, ..."
        assert data["input_tokens"] == 1000
        assert data["output_tokens"] == 500
        # cost = (1000/1e6)*3.00 + (500/1e6)*15.00 = 0.003 + 0.0075 = 0.0105
        assert abs(data["cost_usd"] - 0.0105) < 1e-6

    def test_generate_calls_all_collaborators(self, client, mocks):
        client.post("/generate", json=VALID_PAYLOAD)
        mocks["extract_doc_id"].assert_called_once()
        mocks["read_doc_text"].assert_called_once_with("DOC_ID_123")
        mocks["retrieve_examples"].assert_called_once()
        mocks["get_rules"].assert_called_once()
        mocks["generate_lor"].assert_called_once()
        mocks["log_usage"].assert_called_once()

    def test_generate_bad_doc_url_returns_400(self, client, mocks):
        mocks["extract_doc_id"].side_effect = ValueError("Invalid Google Docs URL")
        response = client.post("/generate", json={**VALID_PAYLOAD, "customer_doc_url": "not-a-url"})
        assert response.status_code == 400
        assert "Cannot read customer doc" in response.json()["detail"]

    def test_generate_unreadable_doc_returns_400(self, client, mocks):
        mocks["read_doc_text"].side_effect = Exception("Doc not accessible")
        response = client.post("/generate", json=VALID_PAYLOAD)
        assert response.status_code == 400
        assert "Cannot read customer doc" in response.json()["detail"]

    def test_generate_missing_required_field_returns_422(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "employee_email"}
        response = client.post("/generate", json=payload)
        assert response.status_code == 422

    def test_generate_pipeline_failure_returns_502(self, client, mocks):
        mocks["generate_lor"].side_effect = RuntimeError("Bedrock timeout")
        response = client.post("/generate", json=VALID_PAYLOAD)
        assert response.status_code == 502
        assert "Generation failed" in response.json()["detail"]
