from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .config import settings

ModelProvider = Literal["local", "fireworks", "amd"]


@dataclass(frozen=True)
class RoutingDecision:
    provider: ModelProvider
    model: str
    reason: str
    estimated_tokens: int
    estimated_cost_usd: float


MODEL_PRICING = {
    "local": 0.0,
    "fireworks": 0.0025,
    "amd": 0.0035,
}


def estimate_tokens(text: str) -> int:
    return max(32, (len(text.strip()) // 4) + 16)


def select_model(
    task_type: str,
    *,
    expected_cost: str = "low",
    confidence: float = 0.75,
    required_accuracy: str = "medium",
    context: str = "",
) -> RoutingDecision:
    task = task_type.lower().strip()
    tokens = estimate_tokens(f"{task} {context}")

    high_accuracy = required_accuracy in {"high", "critical"}
    expensive_ok = expected_cost in {"medium", "high"}
    low_confidence = confidence < 0.72

    if task in {"storage", "health", "status"} and not high_accuracy:
        provider = "local"
        model = settings.local_model
        reason = "Operational check is deterministic and cheapest on a local/small model."
    elif task in {"review_pr", "approve", "safe_to_merge"}:
        provider = "amd" if high_accuracy or low_confidence else "fireworks"
        model = settings.amd_model if provider == "amd" else settings.fireworks_model
        reason = (
            "Code-review and approval decisions prefer higher accuracy, so the router "
            "escalates beyond the local model."
        )
    elif task in {"email_triage", "goal"}:
        if expensive_ok or low_confidence:
            provider = "fireworks"
            model = settings.fireworks_model
            reason = "Summarization and prioritization benefit from a remote reasoning model."
        else:
            provider = "local"
            model = settings.local_model
            reason = "Low-risk triage can stay local to minimize cost."
    else:
        if high_accuracy or low_confidence:
            provider = "fireworks"
            model = settings.fireworks_model
            reason = "Defaulting to remote reasoning because the task needs broader context."
        else:
            provider = "local"
            model = settings.local_model
            reason = "Defaulting to local for a cheap, fast first pass."

    estimated_cost = round(tokens / 1000 * MODEL_PRICING[provider], 4)
    return RoutingDecision(provider, model, reason, tokens, estimated_cost)
