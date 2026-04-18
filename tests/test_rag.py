import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))


def test_index_letter_adds_to_collection():
    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("rag.chromadb.PersistentClient", return_value=mock_client):
        from rag import index_letter
        index_letter(
            doc_id="doc123",
            text="This is an approved EB-1A letter...",
            lor_type="EB1A",
            field="AI",
            approved_date="2026-04-01"
        )

    mock_collection.add.assert_called_once()
    call_kwargs = mock_collection.add.call_args[1]
    assert "doc123" in call_kwargs["ids"]
    assert call_kwargs["metadatas"][0]["lor_type"] == "EB1A"


def test_retrieve_examples_returns_texts():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Letter A text", "Letter B text", "Letter C text"]]
    }
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("rag.chromadb.PersistentClient", return_value=mock_client):
        from rag import retrieve_examples
        results = retrieve_examples(
            query="AI researcher extraordinary ability",
            lor_type="EB1A",
            n=3
        )

    assert len(results) == 3
    assert results[0] == "Letter A text"


def test_retrieve_examples_empty_collection():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": []}
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("rag.chromadb.PersistentClient", return_value=mock_client):
        from rag import retrieve_examples
        results = retrieve_examples(query="anything", lor_type="EB1A", n=3)

    assert results == []
