import pytest

from mistral_desktop import agent_service, config
from mistral_desktop.agent_service import (
    complete_chat,
    next_color,
    provider_for_agent,
    seed_default_agents,
)
from mistral_desktop.models import Agent, new_id
from mistral_desktop.providers import HF_BASE_URL, MISTRAL_BASE_URL, ProviderError
from tests.mock_server import MockHandler


@pytest.fixture(autouse=True)
def no_keyring(monkeypatch):
    monkeypatch.setattr(config, "_keyring", lambda: None)
    for var in ("MISTRAL_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(var, raising=False)


def test_seed_default_agents_idempotent(store):
    seed_default_agents(store)
    seed_default_agents(store)
    agents = store.list_agents()
    assert len(agents) == 2
    assert {a.model for a in agents} == {"mistral-large-latest", "mistral-small-latest"}
    assert all(a.provider == "mistral" and a.source == "mistral" for a in agents)


def test_next_color_cycles():
    agents = [Agent(id=str(i), name=str(i), provider="mistral", model="m", color=c)
              for i, c in enumerate(agent_service.PALETTE[:3])]
    assert next_color(agents) == agent_service.PALETTE[3]


def test_provider_mistral_requires_key(settings):
    agent = Agent(id=new_id(), name="a", provider="mistral", model="mistral-large-latest")
    with pytest.raises(ProviderError, match="Mistral API key"):
        provider_for_agent(agent, settings)


def test_provider_mistral_from_env(settings, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "env-key")
    agent = Agent(id=new_id(), name="a", provider="mistral", model="m")
    p = provider_for_agent(agent, settings)
    assert p.base_url == MISTRAL_BASE_URL and p.api_key == "env-key"


def test_provider_hf_requires_token(settings):
    agent = Agent(id=new_id(), name="a", provider="huggingface", model="Qwen/Qwen2.5-7B-Instruct")
    with pytest.raises(ProviderError, match="Hugging Face token"):
        provider_for_agent(agent, settings)


def test_provider_hf_from_env(settings, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_env")
    agent = Agent(id=new_id(), name="a", provider="huggingface", model="m")
    p = provider_for_agent(agent, settings)
    assert p.base_url == HF_BASE_URL and p.api_key == "hf_env"


def test_provider_custom_uses_agent_fields(settings):
    agent = Agent(id=new_id(), name="local", provider="openai_compatible", model="llama3",
                  base_url="http://localhost:11434/v1", api_key="k")
    p = provider_for_agent(agent, settings)
    assert p.base_url == "http://localhost:11434/v1" and p.api_key == "k"


def test_provider_space_not_chatable(settings):
    agent = Agent(id=new_id(), name="s", provider="huggingface_space", model="a/b", space_id="a/b")
    with pytest.raises(ProviderError, match="Space"):
        provider_for_agent(agent, settings)
    assert agent.is_space


def test_complete_chat_end_to_end_against_mock_server(mock_server, settings):
    agent = Agent(id=new_id(), name="mock", provider="openai_compatible", model="m",
                  base_url=mock_server, api_key="secret", system_prompt="be terse")
    out = complete_chat(agent, settings, [{"role": "user", "content": "hi"}])
    assert out == "Hello, world"
    assert MockHandler.last_payload["messages"][0]["role"] == "system"


def test_test_mistral_key_ok(mock_server, monkeypatch):
    from mistral_desktop.providers import OpenAICompatProvider

    monkeypatch.setattr(agent_service, "mistral_provider",
                        lambda key: OpenAICompatProvider(mock_server, "secret"))
    assert "OK" in agent_service.test_mistral_key("anything")


def test_test_mistral_key_rejected(mock_server, monkeypatch):
    from mistral_desktop.providers import OpenAICompatProvider

    monkeypatch.setattr(agent_service, "mistral_provider",
                        lambda key: OpenAICompatProvider(mock_server, "wrong-key"))
    assert "rejected" in agent_service.test_mistral_key("anything")


def test_test_hf_token_rejected(mock_server, monkeypatch):
    from mistral_desktop.providers import OpenAICompatProvider

    monkeypatch.setattr(agent_service, "huggingface_provider",
                        lambda token: OpenAICompatProvider(mock_server, "bad-token"))
    assert "rejected" in agent_service.test_hf_token("bad-token")
