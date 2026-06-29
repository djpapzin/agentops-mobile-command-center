from pathlib import Path

from app.db import init_db, recent_approvals, summary
from app.demo import (
    _operator_one_liner,
    build_safe_to_merge_card,
    handle_command,
    review_email_triage,
)


def test_goal_updates_state(tmp_path: Path):
    db = tmp_path / "app.sqlite3"
    init_db(db)
    result = handle_command("/goal Ship the hackathon MVP", db_path=db)
    assert "Goal updated" in result.text
    assert result.payload["goal"] == "Ship the hackathon MVP"
    assert summary(db)["current_goal"] == "Ship the hackathon MVP"


def test_review_creates_pending_approval(tmp_path: Path):
    db = tmp_path / "app.sqlite3"
    init_db(db)
    result = handle_command("/review_pr https://github.com/example/repo/pull/42", db_path=db)
    assert "PR Review" in result.text
    approvals = recent_approvals(path=db)
    assert approvals and approvals[0]["status"] == "pending"


def test_live_demo_reports_live_flag_or_fallback(tmp_path: Path):
    db = tmp_path / "app.sqlite3"
    init_db(db)
    result = handle_command("/live_demo", db_path=db)
    assert "Live demo" in result.text
    assert "live" in result.payload
    assert result.payload["task_type"] == "live_demo"
    assert len(result.payload["result_summary"].splitlines()) == 1


def test_operator_one_liner_replaces_verbose_model_copy():
    verbose = "The user wants a single short confirmation line. Requirements: include provider."
    assert _operator_one_liner(verbose, provider="fireworks", live=True) == (
        "Smoke test completed via fireworks; completion mode: live."
    )


def test_email_triage_returns_ranked_items():
    triage = review_email_triage()
    assert triage["emails"][0]["risk"] == "high"
    assert len(triage["emails"]) == 3


def test_safe_to_merge_card_has_routing():
    card = build_safe_to_merge_card()
    assert "routing" in card
    assert card["title"] == "Safe-to-merge decision card"
