import pytest

from mistral_desktop.providers import (
    HF_BASE_URL,
    MISTRAL_BASE_URL,
    OpenAICompatProvider,
    ProviderError,
    huggingface_provider,
    mistral_provider,
)
from tests.mock_server import MockHandler


def test_stream_chat_collects_text(mock_server):
    p = OpenAICompatProvider(mock_server, "secret")
    chunks = list(p.stream_chat(model="mistral-large-latest", messages=[{"role": "user", "content": "hi"}]))
    assert "".join(c.text for c in chunks) == "Hello, world"
    assert chunks[-1].finish_reason == "stop"


def test_system_prompt_prepended_and_stream_flag(mock_server):
    p = OpenAICompatProvider(mock_server, "secret")
    list(p.stream_chat(model="m", messages=[{"role": "user", "content": "hi"}], system_prompt="be terse"))
    payload = MockHandler.last_payload
    assert payload["stream"] is True
    assert payload["messages"][0] == {"role": "system", "content": "be terse"}
    assert payload["messages"][1] == {"role": "user", "content": "hi"}
    assert MockHandler.last_auth == "Bearer secret"


def test_no_key_sends_no_auth_header(mock_server):
    p = OpenAICompatProvider(mock_server, "")
    with pytest.raises(ProviderError, match="invalid api key"):
        list(p.stream_chat(model="m", messages=[{"role": "user", "content": "hi"}]))
    assert MockHandler.last_auth is None


def test_list_models(mock_server):
    p = OpenAICompatProvider(mock_server, "secret")
    models = p.list_models()
    assert [m["id"] for m in models] == ["mistral-large-latest", "mistral-small-latest"]


def test_bad_model_error_detail(mock_server):
    p = OpenAICompatProvider(mock_server, "secret")
    with pytest.raises(ProviderError, match="model not found"):
        list(p.stream_chat(model="bad-model", messages=[{"role": "user", "content": "hi"}]))


def test_base_url_trailing_slash_normalized(mock_server):
    p = OpenAICompatProvider(mock_server + "/", "secret")
    assert p.base_url == mock_server
    assert p.list_models()


def test_unreachable_host():
    p = OpenAICompatProvider("http://127.0.0.1:1/v1", "k", timeout=2)
    with pytest.raises(ProviderError, match="Could not reach"):
        p.list_models()


def test_presets():
    m = mistral_provider("k")
    assert m.base_url == MISTRAL_BASE_URL and m.api_key == "k" and m.name == "Mistral"
    h = huggingface_provider("hf_x")
    assert h.base_url == HF_BASE_URL and h.api_key == "hf_x" and h.name == "Hugging Face"


def test_chat_convenience(mock_server):
    p = OpenAICompatProvider(mock_server, "secret")
    assert p.chat(model="m", messages=[{"role": "user", "content": "hi"}]) == "Hello, world"
