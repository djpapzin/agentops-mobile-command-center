from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import settings
from .demo import CommandResult, handle_command


class TelegramClient(Protocol):
    def get_updates(self, *, offset: int | None = None, timeout: int = 20) -> list[dict[str, Any]]: ...
    def send_message(self, *, chat_id: int | str, text: str) -> None: ...


class TelegramAPIError(RuntimeError):
    pass


@dataclass
class TelegramHTTPClient:
    token: str
    base_url: str = "https://api.telegram.org"
    timeout: int = 30

    def _url(self, method: str) -> str:
        return f"{self.base_url}/bot{self.token}/{method}"

    def _post(self, method: str, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(method),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - network errors are runtime-only
            raise TelegramAPIError(str(exc)) from exc
        if not data.get("ok", False):
            raise TelegramAPIError(str(data))
        return data["result"]

    def get_updates(self, *, offset: int | None = None, timeout: int = 20) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message", "edited_message"]}
        if offset is not None:
            payload["offset"] = offset
        result = self._post("getUpdates", payload)
        return list(result)

    def send_message(self, *, chat_id: int | str, text: str) -> None:
        self._post("sendMessage", {"chat_id": chat_id, "text": text})


@dataclass
class TelegramBot:
    client: TelegramClient
    db_path: Path | None = None
    allowed_chat_ids: list[str] | None = None

    def _is_allowed(self, chat_id: int | str) -> bool:
        if not self.allowed_chat_ids:
            return True
        return str(chat_id) in {str(item) for item in self.allowed_chat_ids}

    def handle_update(self, update: dict[str, Any]) -> CommandResult | None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return None
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or not self._is_allowed(chat_id):
            return None
        text = (message.get("text") or "").strip()
        if not text:
            return None
        if text == "/start":
            text = "/help"
        result = handle_command(text, db_path=self.db_path)
        self.client.send_message(chat_id=chat_id, text=result.text)
        return result

    def run_once(self, *, offset: int | None = None, timeout: int = 20) -> int:
        updates = self.client.get_updates(offset=offset, timeout=timeout)
        next_offset = offset or 0
        for update in updates:
            next_offset = max(next_offset, int(update.get("update_id", 0)) + 1)
            self.handle_update(update)
        return next_offset

    def run_forever(self, *, poll_timeout: int = 20, sleep_seconds: float = 3.0) -> None:
        offset: int | None = None
        while True:  # pragma: no cover - long-running runtime loop
            try:
                offset = self.run_once(offset=offset, timeout=poll_timeout)
            except TelegramAPIError as exc:
                print(f"Telegram API error: {exc}")
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                print("Telegram bot stopped.")
                return


def main() -> int:
    bot_token = getattr(settings, "telegram_bot_token", "")
    allowed_chat_ids = getattr(settings, "telegram_allowed_chat_ids", [])
    poll_timeout = int(getattr(settings, "telegram_poll_timeout_seconds", 20))
    poll_interval = float(getattr(settings, "telegram_poll_interval_seconds", 3.0))

    if not bot_token:
        print("TELEGRAM_BOT_TOKEN is not set; Telegram bot mode is disabled.")
        return 0
    client = TelegramHTTPClient(bot_token)
    bot = TelegramBot(
        client=client,
        db_path=settings.db_path,
        allowed_chat_ids=allowed_chat_ids,
    )
    print("Telegram bot polling started.")
    bot.run_forever(
        poll_timeout=poll_timeout,
        sleep_seconds=poll_interval,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
