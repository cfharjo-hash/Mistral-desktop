from __future__ import annotations

import time
from typing import Iterator

from .config import Settings, resolve_hf_token, resolve_mistral_key
from .models import Agent, new_id
from .providers import (
    ChatProvider,
    OpenAICompatProvider,
    ProviderError,
    huggingface_provider,
    mistral_provider,
)
from .store import Store

PALETTE = [
    "#6c8cff", "#4ec9b0", "#ce9178", "#c586c0", "#dcdcaa",
    "#9cdcfe", "#f78c6c", "#7ee787", "#ff9ff3", "#a5d6ff",
]

DEFAULT_AGENTS = [
    ("Mistral Large", "mistral-large-latest"),
    ("Mistral Small", "mistral-small-latest"),
]


def next_color(existing: list[Agent]) -> str:
    used = {a.color for a in existing}
    for c in PALETTE:
        if c not in used:
            return c
    return PALETTE[len(existing) % len(PALETTE)]


def seed_default_agents(store: Store) -> None:
    if store.list_agents():
        return
    for i, (name, model) in enumerate(DEFAULT_AGENTS):
        store.save_agent(
            Agent(
                id=new_id(),
                name=name,
                provider="mistral",
                model=model,
                source="mistral",
                color=PALETTE[i % len(PALETTE)],
                created_at=time.time() + i,
            )
        )


def provider_for_agent(agent: Agent, settings: Settings) -> ChatProvider:
    if agent.provider == "mistral":
        key = resolve_mistral_key(settings)
        if not key:
            raise ProviderError(
                "No Mistral API key found. Set the MISTRAL_API_KEY environment variable "
                "or add a key in Settings (⚙)."
            )
        return mistral_provider(key)
    if agent.provider == "huggingface":
        token = resolve_hf_token(settings)
        if not token:
            raise ProviderError(
                "No Hugging Face token found. Set HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) "
                "or add a token in Settings (⚙). Get one at huggingface.co/settings/tokens."
            )
        return huggingface_provider(token)
    if agent.provider == "openai_compatible":
        if not agent.base_url:
            raise ProviderError(f"Agent '{agent.name}' has no base URL configured.")
        return OpenAICompatProvider(agent.base_url, agent.api_key, name=agent.name)
    raise ProviderError(
        f"Agent '{agent.name}' is a Hugging Face Space and runs on huggingface.co — "
        "open it in your browser instead of chatting here."
    )


def run_chat(agent: Agent, settings: Settings, messages: list[dict], temperature: float = 0.7) -> Iterator:
    provider = provider_for_agent(agent, settings)
    return provider.stream_chat(
        model=agent.model,
        messages=messages,
        system_prompt=agent.system_prompt or None,
        temperature=temperature,
    )


def complete_chat(agent: Agent, settings: Settings, messages: list[dict], temperature: float = 0.7) -> str:
    return "".join(c.text for c in run_chat(agent, settings, messages, temperature))
