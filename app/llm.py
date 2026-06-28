from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .config import settings
from .router import RoutingDecision, select_model


Opener = Any


@dataclass(frozen=True)
class OpenAICompatibleClient:
    api_key: str
    base_url: str
    timeout: int = 30
    opener: Opener = urllib.request.urlopen

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        system_prompt: str = "You are a concise assistant.",
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(request, self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - runtime network errors
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response did not include any choices")
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content") or choice.get("text") or ""
        text = str(content).strip()
        if not text:
            raise RuntimeError("LLM response was empty")
        return text


def _build_client(provider: str) -> OpenAICompatibleClient | None:
    if provider == "fireworks":
        if not settings.fireworks_api_key:
            return None
        return OpenAICompatibleClient(
            api_key=settings.fireworks_api_key,
            base_url=settings.fireworks_base_url,
            timeout=settings.fireworks_timeout_seconds,
        )
    if provider == "amd":
        if not settings.amd_api_key:
            return None
        return OpenAICompatibleClient(
            api_key=settings.amd_api_key,
            base_url=settings.amd_base_url,
            timeout=settings.amd_timeout_seconds,
        )
    return None


def routed_completion(
    task_type: str,
    prompt: str,
    *,
    expected_cost: str = "low",
    confidence: float = 0.75,
    required_accuracy: str = "medium",
    context: str = "",
    fallback_text: str,
    system_prompt: str = "You are a helpful mobile-first operator assistant.",
    client_factory: Callable[[str], OpenAICompatibleClient | None] = _build_client,
) -> dict[str, Any]:
    decision: RoutingDecision = select_model(
        task_type,
        expected_cost=expected_cost,
        confidence=confidence,
        required_accuracy=required_accuracy,
        context=context,
    )
    payload: dict[str, Any] = {
        "provider": decision.provider,
        "model": decision.model,
        "reason": decision.reason,
        "estimated_tokens": decision.estimated_tokens,
        "estimated_cost_usd": decision.estimated_cost_usd,
        "live": False,
        "live_error": None,
        "text": fallback_text,
    }
    client = client_factory(decision.provider)
    if client is None:
        return payload
    try:
        payload["text"] = client.complete(
            model=decision.model,
            prompt=prompt,
            system_prompt=system_prompt,
        )
        payload["live"] = True
    except Exception as exc:  # pragma: no cover - live runtime fallback
        payload["live_error"] = str(exc)
    return payload
