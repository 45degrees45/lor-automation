import pytest
import json
from unittest.mock import MagicMock, patch



# --- detect_lor_type tests ---

def test_detect_lor_type_eb1a():
    from importer import detect_lor_type
    assert detect_lor_type("This is an EB-1A petition") == "EB1A"


def test_detect_lor_type_niw():
    from importer import detect_lor_type
    assert detect_lor_type("National Interest Waiver application") == "NIW"


def test_detect_lor_type_o1a():
    from importer import detect_lor_type
    assert detect_lor_type("O-1A visa") == "O1A"


def test_detect_lor_type_default():
    from importer import detect_lor_type
    assert detect_lor_type("unknown text") == "EB1A"


# --- summarize_comments_to_rules tests ---

def test_summarize_comments_to_rules_empty_comments_returns_existing():
    from importer import summarize_comments_to_rules
    existing = ["Rule A", "Rule B"]
    result = summarize_comments_to_rules([], lor_type="EB1A", existing_rules=existing)
    assert result == existing


# --- import_document tests ---

def test_import_document_calls_index_letter_when_approved_in_comments():
    mock_bedrock_response_body = MagicMock()
    mock_bedrock_response_body.read.return_value = json.dumps({
        "content": [{"text": '["Updated rule"]'}]
    }).encode()

    mock_bedrock_client = MagicMock()
    mock_bedrock_client.invoke_model.return_value = {"body": mock_bedrock_response_body}

    mock_db = MagicMock()

    with patch("importer.extract_doc_id", return_value="doc_abc") as mock_extract, \
         patch("importer.read_doc_text", return_value="EB-1A petition letter") as mock_text, \
         patch("importer.read_doc_comments", return_value=[
             {"content": "[APPROVED] looks great", "resolved": False}
         ]) as mock_comments, \
         patch("importer.index_letter") as mock_index, \
         patch("importer.get_rules", return_value=[]) as mock_get_rules, \
         patch("importer.save_rules") as mock_save_rules, \
         patch("importer.get_bedrock_client", return_value=mock_bedrock_client):

        from importer import import_document
        result = import_document("https://docs.google.com/document/d/doc_abc/edit", db=mock_db)

    mock_index.assert_called_once()
    call_kwargs = mock_index.call_args[1]
    assert call_kwargs["doc_id"] == "doc_abc"
    assert call_kwargs["lor_type"] == "EB1A"
    assert result["doc_id"] == "doc_abc"
    assert result["lor_type"] == "EB1A"
