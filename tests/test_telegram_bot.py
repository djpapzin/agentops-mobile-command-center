from pathlib import Path

from app.db import init_db
from app.telegram_bot import TelegramBot


class FakeClient:
    def __init__(self, updates: list[dict]):
        self.updates = updates
        self.sent: list[tuple[int | str, str]] = []

    def get_updates(self, *, offset: int | None = None, timeout: int = 20):
        return self.updates

    def send_message(self, *, chat_id: int | str, text: str) -> None:
        self.sent.append((chat_id, text))



def test_bot_processes_start_and_storage(tmp_path: Path):
    db = tmp_path / "agentops.sqlite3"
    init_db(db)
    client = FakeClient(
        [
            {"update_id": 1, "message": {"chat": {"id": 123}, "text": "/start"}},
            {"update_id": 2, "message": {"chat": {"id": 123}, "text": "/storage"}},
        ]
    )
    bot = TelegramBot(client=client, db_path=db)
    next_offset = bot.run_once()

    assert next_offset == 3
    assert len(client.sent) == 2
    assert client.sent[0][1].startswith("Commands:")
    assert "Storage" in client.sent[1][1]


def test_bot_respects_allowed_chat_ids(tmp_path: Path):
    db = tmp_path / "agentops.sqlite3"
    init_db(db)
    client = FakeClient(
        [{"update_id": 1, "message": {"chat": {"id": 999}, "text": "/goal Test"}}]
    )
    bot = TelegramBot(client=client, db_path=db, allowed_chat_ids=["123"])
    bot.run_once()

    assert client.sent == []
