from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "AgentOps Mobile Command Center")
    app_env: str = os.getenv("APP_ENV", "demo")
    db_path: Path = Path(os.getenv("APP_DB_PATH", "./data/agentops.sqlite3"))
    public_url: str = os.getenv("APP_PUBLIC_URL", "http://localhost:8000")
    fireworks_model: str = os.getenv(
        "FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct"
    )
    amd_model: str = os.getenv("AMD_MODEL", "amd/mi300x-llama-3.1-70b")
    local_model: str = os.getenv("LOCAL_MODEL", "local/phi-3-mini")
    demo_pr_url: str = os.getenv(
        "DEMO_PR_URL", "https://github.com/example/repo/pull/42"
    )


settings = Settings()
