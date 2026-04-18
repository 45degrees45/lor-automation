import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))


def _make_doc_snap(doc_url, lor_type="EB1A", field="General"):
    snap = MagicMock()
    snap.to_dict.return_value = {
        "doc_url": doc_url,
        "lor_type": lor_type,
        "field": field,
    }
    return snap


def _make_db(doc_snaps):
    db = MagicMock()
    db.collection.return_value.where.return_value.stream.return_value = iter(doc_snaps)
    return db


# --- Test 1: APPROVED comment → index_letter called, approved_count=1 ---

def test_approved_comment_calls_index_letter():
    snap = _make_doc_snap("https://docs.google.com/document/d/doc123/edit")
    db = _make_db([snap])

    comments = [{"content": "[APPROVED] great letter", "resolved": False}]
    existing_rules = ["Rule A"]

    with patch("feedback.extract_doc_id", return_value="doc123"), \
         patch("feedback.read_doc_comments", return_value=comments), \
         patch("feedback.read_doc_text", return_value="Full letter text"), \
         patch("feedback.get_rules", return_value=existing_rules), \
         patch("feedback.summarize_comments_to_rules", return_value=existing_rules), \
         patch("feedback.save_rules") as mock_save, \
         patch("feedback.index_letter") as mock_index:

        from feedback import run_weekly_feedback
        result = run_weekly_feedback(db)

    assert result["letters_approved"] == 1
    mock_index.assert_called_once()
    call_kwargs = mock_index.call_args[1]
    assert call_kwargs["doc_id"] == "doc123"
    assert call_kwargs["lor_type"] == "EB1A"
    # rules unchanged → save_rules not called
    mock_save.assert_not_called()


# --- Test 2: rules change → save_rules called, updated_count=1 ---

def test_changed_rules_calls_save_rules():
    snap = _make_doc_snap("https://docs.google.com/document/d/doc456/edit", lor_type="NIW")
    db = _make_db([snap])

    existing_rules = ["Old rule"]
    new_rules = ["Old rule", "New rule"]
    comments = [{"content": "please add more detail", "resolved": False}]

    with patch("feedback.extract_doc_id", return_value="doc456"), \
         patch("feedback.read_doc_comments", return_value=comments), \
         patch("feedback.read_doc_text", return_value="Letter text"), \
         patch("feedback.get_rules", return_value=existing_rules), \
         patch("feedback.summarize_comments_to_rules", return_value=new_rules), \
         patch("feedback.save_rules") as mock_save, \
         patch("feedback.index_letter") as mock_index:

        from feedback import run_weekly_feedback
        result = run_weekly_feedback(db)

    assert result["rules_updated"] == 1
    mock_save.assert_called_once_with(db, "NIW", new_rules)
    # no [APPROVED] in comments
    mock_index.assert_not_called()


# --- Test 3: rules unchanged → save_rules NOT called, updated_count=0 ---

def test_unchanged_rules_does_not_call_save_rules():
    snap = _make_doc_snap("https://docs.google.com/document/d/doc789/edit")
    db = _make_db([snap])

    existing_rules = ["Rule A", "Rule B"]
    comments = [{"content": "looks fine", "resolved": False}]

    with patch("feedback.extract_doc_id", return_value="doc789"), \
         patch("feedback.read_doc_comments", return_value=comments), \
         patch("feedback.read_doc_text", return_value="Letter text"), \
         patch("feedback.get_rules", return_value=existing_rules), \
         patch("feedback.summarize_comments_to_rules", return_value=existing_rules), \
         patch("feedback.save_rules") as mock_save, \
         patch("feedback.index_letter") as mock_index:

        from feedback import run_weekly_feedback
        result = run_weekly_feedback(db)

    assert result["rules_updated"] == 0
    mock_save.assert_not_called()
    mock_index.assert_not_called()


# --- Test 4: extract_doc_id raises → error swallowed, counts stay 0 ---

def test_extract_doc_id_raises_error_swallowed():
    snap = _make_doc_snap("https://bad-url")
    db = _make_db([snap])

    with patch("feedback.extract_doc_id", side_effect=ValueError("bad url")), \
         patch("feedback.save_rules") as mock_save, \
         patch("feedback.index_letter") as mock_index:

        from feedback import run_weekly_feedback
        # should not raise
        result = run_weekly_feedback(db)

    assert result["rules_updated"] == 0
    assert result["letters_approved"] == 0
    mock_save.assert_not_called()
    mock_index.assert_not_called()
