from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "AgentOps Mobile Command Center")
    app_env: str = os.getenv("APP_ENV", "demo")
    db_path: Path = Path(os.getenv("APP_DB_PATH", "./data/agentops.sqlite3"))
    public_url: str = os.getenv("APP_PUBLIC_URL", "http://localhost:8000")
    fireworks_model: str = os.getenv(
        "FIREWORKS_MODEL", "accounts/fireworks/models/kimi-k2p6"
    )
    fireworks_api_key: str = os.getenv("FIREWORKS_API_KEY", "")
    fireworks_base_url: str = os.getenv(
        "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
    )
    fireworks_timeout_seconds: int = int(os.getenv("FIREWORKS_TIMEOUT_SECONDS", "30"))
    amd_model: str = os.getenv("AMD_MODEL", "amd/mi300x-llama-3.1-70b")
    amd_api_key: str = os.getenv("AMD_API_KEY", "")
    amd_base_url: str = os.getenv("AMD_BASE_URL", "https://api.amd.com/v1")
    amd_timeout_seconds: int = int(os.getenv("AMD_TIMEOUT_SECONDS", "30"))
    local_model: str = os.getenv("LOCAL_MODEL", "local/phi-3-mini")
    demo_pr_url: str = os.getenv(
        "DEMO_PR_URL", "https://github.com/example/repo/pull/42"
    )
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_allowed_chat_ids: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", ""))
    )
    telegram_poll_timeout_seconds: int = int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "20"))
    telegram_poll_interval_seconds: float = float(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "3"))


settings = Settings()
