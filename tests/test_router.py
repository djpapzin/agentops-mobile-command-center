from app.router import select_model, estimate_tokens


def test_storage_stays_local():
    decision = select_model("storage", context="check disk")
    assert decision.provider == "local"
    assert "local/small" in decision.reason.lower() or "local" in decision.reason.lower()


def test_pr_review_escalates_to_remote():
    decision = select_model("review_pr", required_accuracy="high", confidence=0.6)
    assert decision.provider in {"amd", "fireworks"}
    assert decision.model
    assert decision.estimated_tokens >= 32


def test_token_estimation_has_floor():
    assert estimate_tokens("") >= 32
    assert estimate_tokens("hello world") >= 32
