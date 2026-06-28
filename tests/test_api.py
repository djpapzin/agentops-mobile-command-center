from pathlib import Path

from fastapi.testclient import TestClient

from app import config
from app.db import init_db
from app.main import app


def test_health_and_demo_endpoints(tmp_path: Path, monkeypatch):
    db = tmp_path / "agentops.sqlite3"
    monkeypatch.setattr(config.settings, "db_path", db)
    init_db(db)
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    demo = client.post("/api/telegram/demo", json={"text": "/storage"})
    assert demo.status_code == 200
    assert "Storage" in demo.json()["reply"]

    runs = client.get("/api/runs")
    assert runs.status_code == 200
    assert "runs" in runs.json()
