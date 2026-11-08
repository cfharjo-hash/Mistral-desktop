from __future__ import annotations

import json
import os
from pathlib import Path

from .config import Settings
from .models import Agent, Conversation


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.conv_dir = self.data_dir / "conversations"
        self.conv_dir.mkdir(exist_ok=True)
        self.agents_file = self.data_dir / "agents.json"
        self.settings_file = self.data_dir / "settings.json"

    def _write_json(self, path: Path, obj, private: bool = False) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        if private:
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    def _read_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def list_agents(self) -> list[Agent]:
        data = self._read_json(self.agents_file, [])
        agents = [Agent.from_dict(d) for d in data]
        agents.sort(key=lambda a: a.created_at)
        return agents

    def get_agent(self, agent_id: str) -> Agent | None:
        for a in self.list_agents():
            if a.id == agent_id:
                return a
        return None

    def find_agent(self, ref: str) -> Agent | None:
        agents = self.list_agents()
        for a in agents:
            if a.id == ref:
                return a
        low = ref.lower()
        for a in agents:
            if a.name.lower() == low or low in a.name.lower():
                return a
        return None

    def save_agent(self, agent: Agent) -> None:
        agents = [a for a in self.list_agents() if a.id != agent.id]
        agents.append(agent)
        self._write_json(self.agents_file, [a.to_dict() for a in agents], private=True)

    def delete_agent(self, agent_id: str) -> bool:
        agents = self.list_agents()
        remaining = [a for a in agents if a.id != agent_id]
        if len(remaining) == len(agents):
            return False
        self._write_json(self.agents_file, [a.to_dict() for a in remaining], private=True)
        conv = self.conv_dir / f"{agent_id}.json"
        if conv.exists():
            conv.unlink()
        return True

    def load_conversation(self, agent_id: str) -> Conversation:
        return Conversation.from_dict(
            self._read_json(self.conv_dir / f"{agent_id}.json", {"agent_id": agent_id, "messages": []})
        )

    def save_conversation(self, conv: Conversation) -> None:
        self._write_json(self.conv_dir / f"{conv.agent_id}.json", conv.to_dict())

    def load_settings(self) -> Settings:
        return Settings.from_dict(self._read_json(self.settings_file, {}))

    def save_settings(self, settings: Settings) -> None:
        self._write_json(self.settings_file, settings.to_dict(), private=True)
