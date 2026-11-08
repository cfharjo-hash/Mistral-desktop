import json

import pytest
import requests

from mistral_desktop import hf_api


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        for sub, resp in self.routes:
            if sub in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return FakeResponse({"error": "nf"}, 404)


MODELS_PAYLOAD = [
    {
        "id": "Qwen/Qwen2.5-7B-Instruct",
        "likes": 12000,
        "downloads": 500000,
        "pipeline_tag": "text-generation",
        "tags": ["transformers", "chat", "conversational"],
        "library_name": "transformers",
        "gated": False,
    },
    {
        "id": "some/embedding-model",
        "likes": 5,
        "downloads": 10,
        "pipeline_tag": "sentence-similarity",
        "tags": ["sentence-transformers"],
    },
]

SPACES_PAYLOAD = [
    {"id": "smolagents/computer-agent", "likes": 982, "sdk": "gradio",
     "cardData": {"title": "Computer Agent"}, "tags": ["agent"]},
]


def test_search_models_parses_and_passes_params():
    session = FakeSession([("/api/models", FakeResponse(MODELS_PAYLOAD))])
    models = hf_api.search_models("qwen", limit=10, session=session)
    assert [m.id for m in models] == ["Qwen/Qwen2.5-7B-Instruct", "some/embedding-model"]
    assert models[0].likes == 12000
    assert models[0].chat_capable is True
    assert models[1].chat_capable is False
    url, params = session.calls[0]
    assert params["search"] == "qwen"
    assert params["pipeline_tag"] == "text-generation"
    assert params["limit"] == "10"


def test_search_models_empty_pipeline_tag_omitted():
    session = FakeSession([("/api/models", FakeResponse([]))])
    hf_api.search_models(pipeline_tag="", session=session)
    assert "pipeline_tag" not in session.calls[0][1]


def test_search_spaces_parses_card_title():
    session = FakeSession([("/api/spaces", FakeResponse(SPACES_PAYLOAD))])
    spaces = hf_api.search_spaces("agent", session=session)
    assert spaces[0].id == "smolagents/computer-agent"
    assert spaces[0].title == "Computer Agent"
    assert spaces[0].sdk == "gradio"


def test_inference_providers_filters_non_dict():
    payload = {"id": "x", "inferenceProviderMapping": {"featherless-ai": {"status": "live"}, "junk": "nope"}}
    session = FakeSession([("/api/models/x", FakeResponse(payload))])
    providers = hf_api.inference_providers("x", session=session)
    assert list(providers) == ["featherless-ai"]


def test_http_error_raises_hferror():
    session = FakeSession([("/api/models", FakeResponse({"error": "boom"}, status=500))])
    with pytest.raises(hf_api.HFError, match="500"):
        hf_api.search_models(session=session)


def test_network_error_raises_hferror():
    session = FakeSession([("/api/models", requests.ConnectionError("down"))])
    with pytest.raises(hf_api.HFError, match="Network error"):
        hf_api.search_models(session=session)


def test_urls():
    assert hf_api.space_url("a/b") == "https://huggingface.co/spaces/a/b"
    assert hf_api.model_url("a/b") == "https://huggingface.co/a/b"
