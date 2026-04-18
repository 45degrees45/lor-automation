import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))

MOCK_RESPONSE = {
    "content": [{"text": "Dear Reviewer, I am writing to support..."}],
    "usage": {"input_tokens": 800, "output_tokens": 600}
}


def test_generate_lor_returns_text_and_tokens():
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps(MOCK_RESPONSE).encode())
    }

    with patch("generator.get_bedrock_client", return_value=mock_client):
        from generator import generate_lor
        result = generate_lor(
            lor_type="EB1A",
            customer_profile="John is a top AI researcher...",
            rag_examples=["Example letter 1", "Example letter 2"],
            writing_rules=["Always quantify impact", "Use 'original contribution' phrasing"],
            recommender_name="Dr. Smith",
            recommender_title="Professor",
            recommender_org="MIT"
        )

    assert "text" in result
    assert result["text"].startswith("Dear")
    assert result["input_tokens"] == 800
    assert result["output_tokens"] == 600


def test_generate_lor_prompt_includes_lor_type():
    from generator import build_prompt
    prompt = build_prompt(
        lor_type="NIW",
        customer_profile="Jane works in healthcare...",
        rag_examples=[],
        writing_rules=[],
        recommender_name="Dr. Lee",
        recommender_title="Director",
        recommender_org="Johns Hopkins"
    )
    assert "NIW" in prompt or "National Interest Waiver" in prompt


def test_build_prompt_includes_recommender():
    from generator import build_prompt
    prompt = build_prompt(
        lor_type="EB1A",
        customer_profile="Test profile",
        rag_examples=["Gold example"],
        writing_rules=["Rule 1"],
        recommender_name="Dr. Jane Doe",
        recommender_title="CTO",
        recommender_org="Acme Corp"
    )
    assert "Dr. Jane Doe" in prompt
    assert "CTO" in prompt
    assert "Acme Corp" in prompt
    assert "Gold example" in prompt
    assert "Rule 1" in prompt
