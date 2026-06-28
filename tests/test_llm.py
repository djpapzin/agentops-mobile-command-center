from __future__ import annotations

import json
from typing import Any

import pytest

from app.llm import OpenAICompatibleClient, routed_completion


class FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeOpener:
    def __init__(self, response_payload: dict[str, Any]):
        self.response_payload = response_payload
        self.requests: list[Any] = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        return FakeResponse(self.response_payload)



def test_openai_compatible_client_sends_chat_completion_request():
    opener = FakeOpener({"choices": [{"message": {"content": "live output"}}]})
    client = OpenAICompatibleClient(
        api_key="secret-token",
        base_url="https://example.test/v1",
        opener=opener,
    )

    text = client.complete(model="demo-model", prompt="Hello world", system_prompt="You are concise.")

    assert text == "live output"
    assert len(opener.requests) == 1
    request, timeout = opener.requests[0]
    assert timeout == 30
    assert request.full_url == "https://example.test/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret-token"


def test_routed_completion_uses_live_text_when_client_available():
    def client_factory(provider: str):
        assert provider == "fireworks"
        return OpenAICompatibleClient(
            api_key="token",
            base_url="https://example.test/v1",
            opener=FakeOpener({"choices": [{"message": {"content": "remote result"}}]}),
        )

    result = routed_completion(
        "goal",
        "Ship the MVP",
        required_accuracy="high",
        confidence=0.6,
        fallback_text="local fallback",
        client_factory=client_factory,
    )

    assert result["provider"] == "fireworks"
    assert result["live"] is True
    assert result["text"] == "remote result"


def test_routed_completion_falls_back_when_no_remote_client_exists():
    result = routed_completion(
        "review_pr",
        "https://github.com/example/repo/pull/42",
        required_accuracy="high",
        confidence=0.6,
        fallback_text="fallback review",
        client_factory=lambda provider: None,
    )

    assert result["provider"] == "amd"
    assert result["live"] is False
    assert result["text"] == "fallback review"
