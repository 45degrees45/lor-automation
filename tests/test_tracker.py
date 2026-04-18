import pytest
from unittest.mock import MagicMock, patch



def test_log_usage_writes_correct_fields():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    from tracker import log_usage
    returned_cost = log_usage(
        db=mock_db,
        employee_email="emp@co.com",
        doc_id="doc123",
        lor_type="EB1A",
        input_tokens=1000,
        output_tokens=500,
        model_id="us.anthropic.claude-sonnet-4-6-20250630-v1:0"
    )

    assert returned_cost == pytest.approx(0.010500, rel=1e-3)
    mock_collection.add.assert_called_once()
    call_args = mock_collection.add.call_args[0][0]
    assert call_args["employee_email"] == "emp@co.com"
    assert call_args["lor_type"] == "EB1A"
    assert call_args["input_tokens"] == 1000
    assert call_args["output_tokens"] == 500
    assert call_args["cost_usd"] == pytest.approx(0.010500, rel=1e-3)
    assert "timestamp" in call_args


def test_calculate_cost_correct():
    from config.pricing import calculate_cost
    cost = calculate_cost(
        "us.anthropic.claude-sonnet-4-6-20250630-v1:0",
        input_tokens=1_000_000,
        output_tokens=0
    )
    assert cost == pytest.approx(3.00)


def test_calculate_cost_output_only():
    from config.pricing import calculate_cost
    cost = calculate_cost(
        "us.anthropic.claude-sonnet-4-6-20250630-v1:0",
        input_tokens=0,
        output_tokens=1_000_000
    )
    assert cost == pytest.approx(15.00)
