from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Iterator, Optional


class ProviderError(Exception):
    pass


@dataclass
class ChatChunk:
    text: str = ""
    finish_reason: Optional[str] = None


class ChatProvider(abc.ABC):
    name: str = "provider"
    base_url: str = ""

    @abc.abstractmethod
    def list_models(self) -> list[dict]:
        ...

    @abc.abstractmethod
    def stream_chat(self, *, model: str, messages: list[dict], system_prompt: str | None = None,
                    temperature: float = 0.7, max_tokens: int | None = None) -> Iterator[ChatChunk]:
        ...

    def chat(self, **kwargs) -> str:
        return "".join(c.text for c in self.stream_chat(**kwargs))
