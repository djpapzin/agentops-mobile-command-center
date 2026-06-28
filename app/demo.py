from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import settings
from .db import (
    add_approval,
    get_state,
    latest_pending_approval,
    log_run,
    recent_runs,
    resolve_approval,
    set_state,
    summary,
    init_db,
)
from .llm import routed_completion
from .router import select_model


@dataclass(frozen=True)
class CommandResult:
    text: str
    payload: dict[str, Any]


SAMPLE_PR = {
    "title": "Refactor agent routing to reduce cost on low-risk tasks",
    "author": "demo-contributor",
    "checks": ["pytest", "docker build", "lint"],
    "files_changed": 7,
    "risk": "medium",
    "summary": "This PR moves the routing rules into a dedicated module and keeps the hot path small.",
}

SAMPLE_EMAILS = [
    {"from": "alerts@cloud.example", "subject": "Storage at 91% on demo-vm", "risk": "high"},
    {"from": "noreply@calendar.example", "subject": "Meeting moved to tomorrow", "risk": "low"},
    {"from": "boss@example.com", "subject": "Need a quick decision on the PR", "risk": "high"},
]

RISK_ORDER = {"high": 0, "medium": 1, "low": 2}


def _db_path(db_path: Path | None) -> Path:
    return db_path or settings.db_path


def _ensure_db(db_path: Path | None = None) -> Path:
    path = _db_path(db_path)
    init_db(path)
    return path


def _record(
    task_type: str,
    result_summary: str,
    *,
    expected_cost: str = "low",
    confidence: float = 0.8,
    required_accuracy: str = "medium",
    context: str = "",
    approval_status: str = "none",
    prompt: str | None = None,
    system_prompt: str = "You are a helpful mobile-first operator assistant.",
    db_path: Path | None = None,
) -> dict[str, Any]:
    path = _ensure_db(db_path)
    live = None
    if prompt:
        live = routed_completion(
            task_type,
            prompt,
            expected_cost=expected_cost,
            confidence=confidence,
            required_accuracy=required_accuracy,
            context=context,
            fallback_text=result_summary,
            system_prompt=system_prompt,
        )
        result_summary = live["text"]
        provider = live["provider"]
        model_name = live["model"]
        estimated_tokens = live["estimated_tokens"]
        estimated_cost_usd = live["estimated_cost_usd"]
        decision_reason = live["reason"]
        live_used = live["live"]
        live_error = live["live_error"]
    else:
        decision = select_model(
            task_type,
            expected_cost=expected_cost,
            confidence=confidence,
            required_accuracy=required_accuracy,
            context=context,
        )
        provider = decision.provider
        model_name = decision.model
        estimated_tokens = decision.estimated_tokens
        estimated_cost_usd = decision.estimated_cost_usd
        decision_reason = decision.reason
        live_used = False
        live_error = None
    run_id = log_run(
        task_type=task_type,
        model_provider=provider,
        model_name=model_name,
        estimated_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost_usd,
        decision_reason=decision_reason,
        result_summary=result_summary,
        approval_status=approval_status,
        path=path,
    )
    return {
        "run_id": run_id,
        "task_type": task_type,
        "model_provider": provider,
        "model_name": model_name,
        "estimated_tokens": estimated_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "decision_reason": decision_reason,
        "result_summary": result_summary,
        "approval_status": approval_status,
        "live": live_used,
        "live_error": live_error,
    }


def handle_command(text: str, *, db_path: Path | None = None) -> CommandResult:
    path = _ensure_db(db_path)
    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if command == "/goal":
        goal = arg or "No goal supplied"
        set_state("current_goal", goal, path=path)
        record = _record(
            "goal",
            f"Goal set to: {goal}",
            expected_cost="low",
            confidence=0.7,
            required_accuracy="medium",
            context=goal,
            prompt=f"Turn this goal into a concise mobile-friendly action item list: {goal}",
            db_path=path,
        )
        return CommandResult(
            text=f"🎯 Goal updated\n{record['result_summary']}\nModel: {record['model_name']}",
            payload={"goal": goal, **record},
        )

    if command == "/status":
        current_goal = get_state("current_goal", path=path)
        runs = recent_runs(5, path=path)
        record = _record(
            "status",
            f"Status assembled for current goal: {current_goal}",
            expected_cost="low",
            confidence=0.95,
            required_accuracy="medium",
            context=current_goal,
            db_path=path,
        )
        payload = {
            **record,
            "current_goal": current_goal,
            "recent_runs": runs,
            "summary": summary(path=path),
        }
        lines = [
            "📡 Status",
            f"Goal: {current_goal}",
            f"Pending approvals: {payload['summary']['pending_approvals']}",
            "Recent runs:",
        ]
        lines.extend(
            [f"- #{r['id']} {r['task_type']} → {r['model_name']} ({r['approval_status']})" for r in runs[:5]]
            or ["- none yet"]
        )
        return CommandResult(text="\n".join(lines), payload=payload)

    if command == "/storage":
        usage = shutil.disk_usage(path.parent)
        percent = round((usage.used / usage.total) * 100, 1)
        health = "healthy" if percent < 85 else "attention-needed"
        record = _record(
            "storage",
            f"Disk usage at {percent}% ({health}).",
            expected_cost="low",
            confidence=0.99,
            required_accuracy="low",
            context=str(usage),
            db_path=path,
        )
        payload = {
            **record,
            "disk_total_gb": round(usage.total / 1_000_000_000, 2),
            "disk_used_gb": round(usage.used / 1_000_000_000, 2),
            "disk_free_gb": round(usage.free / 1_000_000_000, 2),
            "disk_percent": percent,
            "health": health,
        }
        text_out = (
            f"💾 Storage\nUsed: {payload['disk_used_gb']} GB / {payload['disk_total_gb']} GB\n"
            f"Free: {payload['disk_free_gb']} GB\nHealth: {health}\nModel: {record['model_name']}"
        )
        return CommandResult(text=text_out, payload=payload)

    if command == "/review_pr":
        pr_url = arg or settings.demo_pr_url
        card = {
            "title": SAMPLE_PR["title"],
            "url": pr_url,
            "author": SAMPLE_PR["author"],
            "checks": SAMPLE_PR["checks"],
            "files_changed": SAMPLE_PR["files_changed"],
            "risk": SAMPLE_PR["risk"],
            "summary": SAMPLE_PR["summary"],
            "recommendation": "safe-to-merge" if SAMPLE_PR["risk"] != "high" else "needs-human-review",
        }
        record = _record(
            "review_pr",
            f"PR reviewed: {card['title']} ({card['recommendation']}).",
            expected_cost="medium",
            confidence=0.78,
            required_accuracy="high",
            context=pr_url,
            approval_status="pending",
            prompt=(
                "Review this pull request for a mobile operator and return a concise summary, "
                "risk call, and next action: "
                f"{pr_url}"
            ),
            system_prompt="You write tight GitHub review summaries for mobile operators.",
            db_path=path,
        )
        approval_id = add_approval(card["title"], {**card, **record}, status="pending", path=path)
        text_out = (
            f"🧾 PR Review\nTitle: {card['title']}\nRisk: {card['risk']}\n"
            f"Recommendation: {card['recommendation']}\nPending approval id: {approval_id}\nModel: {record['model_name']}"
        )
        return CommandResult(text=text_out, payload={**record, "approval_id": approval_id, "card": card})

    if command == "/approve":
        latest = latest_pending_approval(path=path)
        if latest:
            resolve_approval(latest["id"], path=path)
            approved_text = f"Approved decision card #{latest['id']}: {latest['title']}"
        else:
            approved_text = "No pending approval card was found."
        record = _record(
            "approve",
            approved_text,
            expected_cost="low",
            confidence=0.92,
            required_accuracy="high",
            context=approved_text,
            approval_status="approved" if latest else "none",
            prompt=f"Summarize the approval decision and next step: {approved_text}",
            system_prompt="You write crisp approval acknowledgements for operators.",
            db_path=path,
        )
        return CommandResult(
            text=f"✅ {approved_text}\nModel: {record['model_name']}",
            payload={**record, "approved": bool(latest), "approved_title": latest["title"] if latest else None},
        )

    if command in {"/help", "help"}:
        record = _record("status", "Help card requested.", expected_cost="low", db_path=path)
        return CommandResult(
            text="Commands:\n/goal <text>\n/status\n/storage\n/review_pr <url>\n/approve",
            payload=record,
        )

    record = _record("status", f"Unknown command: {command}", expected_cost="low", db_path=path)
    return CommandResult(text="Unknown command. Try /help.", payload=record)


def review_email_triage(db_path: Path | None = None) -> dict[str, Any]:
    path = _ensure_db(db_path)
    ranked = sorted(SAMPLE_EMAILS, key=lambda item: RISK_ORDER[item["risk"]])
    record = _record(
        "email_triage",
        "Ranked the inbox by urgency and actionability.",
        expected_cost="medium",
        confidence=0.76,
        required_accuracy="medium",
        context="; ".join(item["subject"] for item in ranked),
        prompt=(
            "Rank these inbox items by urgency and give one-line recommended actions for each: "
            + "; ".join(f"{item['from']} | {item['subject']}" for item in ranked)
        ),
        system_prompt="You prioritize inboxes for a mobile operator.",
        db_path=path,
    )
    return {**record, "emails": ranked}


def build_safe_to_merge_card(db_path: Path | None = None) -> dict[str, Any]:
    path = _ensure_db(db_path)
    review = handle_command(f"/review_pr {settings.demo_pr_url}", db_path=path)
    storage = handle_command("/storage", db_path=path)
    email = review_email_triage(db_path=path)
    safe = storage.payload["health"] == "healthy" and review.payload["card"]["recommendation"] == "safe-to-merge"
    card = {
        "title": "Safe-to-merge decision card",
        "safe_to_merge": safe,
        "signals": {
            "review": review.payload["card"]["recommendation"],
            "storage": storage.payload["health"],
            "email_triage": "attention-needed" if any(e["risk"] == "high" for e in email["emails"]) else "clear",
        },
        "next_action": "approve" if safe else "investigate",
    }
    record = _record(
        "safe_to_merge",
        f"Safe-to-merge card built: {safe}",
        expected_cost="medium",
        confidence=0.85,
        required_accuracy="high",
        context=str(card),
        approval_status="pending" if safe else "blocked",
        db_path=path,
    )
    card["routing"] = record
    return card
