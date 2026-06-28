from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    task_type TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    estimated_tokens INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    decision_reason TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    approval_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    card_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: Path | None = None):
    db_path = Path(path or settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO state(key, value) VALUES (?, ?)",
            ("current_goal", "No active goal yet"),
        )


def set_state(key: str, value: str, path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO state(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_state(key: str, default: str = "", path: Path | None = None) -> str:
    with connect(path) as conn:
        row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def log_run(
    *,
    task_type: str,
    model_provider: str,
    model_name: str,
    estimated_tokens: int,
    estimated_cost_usd: float,
    decision_reason: str,
    result_summary: str,
    approval_status: str,
    path: Path | None = None,
) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO runs(
                created_at, task_type, model_provider, model_name,
                estimated_tokens, estimated_cost_usd, decision_reason,
                result_summary, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utcnow(),
                task_type,
                model_provider,
                model_name,
                estimated_tokens,
                estimated_cost_usd,
                decision_reason,
                result_summary,
                approval_status,
            ),
        )
        return int(cur.lastrowid)


def add_approval(title: str, card: dict[str, Any], status: str = "pending", path: Path | None = None) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO approvals(created_at, title, status, card_json) VALUES (?, ?, ?, ?)",
            (utcnow(), title, status, json.dumps(card, sort_keys=True)),
        )
        return int(cur.lastrowid)


def resolve_approval(approval_id: int, path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "UPDATE approvals SET status='approved', resolved_at=? WHERE id=?",
            (utcnow(), approval_id),
        )


def latest_pending_approval(path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE status='pending' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def recent_runs(limit: int = 10, path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def recent_approvals(limit: int = 10, path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM approvals ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            item["card_json"] = json.loads(item["card_json"])
            data.append(item)
        return data


def summary(path: Path | None = None) -> dict[str, Any]:
    with connect(path) as conn:
        total_runs = conn.execute("SELECT COUNT(*) AS count FROM runs").fetchone()["count"]
        pending = conn.execute(
            "SELECT COUNT(*) AS count FROM approvals WHERE status='pending'"
        ).fetchone()["count"]
        approved = conn.execute(
            "SELECT COUNT(*) AS count FROM approvals WHERE status='approved'"
        ).fetchone()["count"]
    return {
        "current_goal": get_state("current_goal", path=path),
        "total_runs": total_runs,
        "pending_approvals": pending,
        "approved_cards": approved,
    }
