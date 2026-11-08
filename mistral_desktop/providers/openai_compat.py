from __future__ import annotations

import json
from typing import Iterator

import requests

from .base import ChatChunk, ChatProvider, ProviderError


def _error_detail(prefix: str, r: requests.Response) -> str:
    try:
        body = r.json()
        msg = body.get("error", {}).get("message") or r.text[:300]
    except ValueError:
        msg = r.text[:300]
    return f"{prefix} failed ({r.status_code}): {msg}"


class OpenAICompatProvider(ChatProvider):
    def __init__(self, base_url: str, api_key: str = "", name: str = "Custom", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.name = name
        self.timeout = timeout
        self._session = requests.Session()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def list_models(self) -> list[dict]:
        url = f"{self.base_url}/models"
        try:
            r = self._session.get(url, headers=self._headers(), timeout=30)
        except requests.RequestException as e:
            raise ProviderError(f"Could not reach {url}: {e}") from e
        if r.status_code != 200:
            raise ProviderError(_error_detail("Listing models", r))
        data = r.json().get("data", [])
        return [{"id": d.get("id", ""), "owned_by": d.get("owned_by", "")} for d in data if d.get("id")]

    def stream_chat(self, *, model: str, messages: list[dict], system_prompt: str | None = None,
                    temperature: float = 0.7, max_tokens: int | None = None) -> Iterator[ChatChunk]:
        msgs = list(messages)
        if system_prompt:
            msgs = [{"role": "system", "content": system_prompt}] + msgs
        payload = {"model": model, "messages": msgs, "stream": True, "temperature": temperature}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        url = f"{self.base_url}/chat/completions"
        try:
            r = self._session.post(url, headers=self._headers(), json=payload, stream=True, timeout=self.timeout)
        except requests.RequestException as e:
            raise ProviderError(f"Could not reach {url}: {e}") from e
        if r.status_code != 200:
            raise ProviderError(_error_detail("Chat", r))
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            text = delta.get("content") or ""
            if text:
                yield ChatChunk(text=text)
            finish = choice.get("finish_reason")
            if finish:
                yield ChatChunk(text="", finish_reason=finish)
