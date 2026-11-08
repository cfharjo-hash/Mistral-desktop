from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Agent:
    id: str
    name: str
    provider: str
    model: str
    system_prompt: str = ""
    source: str = "custom"
    base_url: str = ""
    api_key: str = ""
    space_id: str = ""
    color: str = "#6c8cff"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "source": self.source,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "space_id": self.space_id,
            "color": self.color,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        return cls(
            id=d["id"],
            name=d.get("name") or d["id"],
            provider=d.get("provider", "mistral"),
            model=d.get("model", ""),
            system_prompt=d.get("system_prompt", ""),
            source=d.get("source", "custom"),
            base_url=d.get("base_url", ""),
            api_key=d.get("api_key", ""),
            space_id=d.get("space_id", ""),
            color=d.get("color", "#6c8cff"),
            created_at=d.get("created_at", time.time()),
        )

    @property
    def is_space(self) -> bool:
        return self.provider == "huggingface_space" or bool(self.space_id)


@dataclass
class Message:
    role: str
    content: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "ts": self.ts}

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(role=d.get("role", "user"), content=d.get("content", ""), ts=d.get("ts", time.time()))

    def to_api(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class Conversation:
    agent_id: str
    messages: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"agent_id": self.agent_id, "messages": [m.to_dict() for m in self.messages]}

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        return cls(
            agent_id=d.get("agent_id", ""),
            messages=[Message.from_dict(m) for m in d.get("messages", [])],
        )
