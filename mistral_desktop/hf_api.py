from __future__ import annotations

from dataclasses import dataclass, field

import requests

API_BASE = "https://huggingface.co/api"
USER_AGENT = "mistral-desktop/0.1"
CHAT_PIPELINE_TAGS = {"text-generation", "conversational", "text2text-generation"}
CHAT_TAG_HINTS = {"conversational", "chat", "text-generation-inference", "endpoints_compatible"}


class HFError(Exception):
    pass


@dataclass
class HFModel:
    id: str
    likes: int = 0
    downloads: int = 0
    pipeline_tag: str = ""
    tags: list = field(default_factory=list)
    library_name: str = ""
    gated: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "HFModel":
        return cls(
            id=d.get("id", ""),
            likes=int(d.get("likes") or 0),
            downloads=int(d.get("downloads") or 0),
            pipeline_tag=d.get("pipeline_tag") or "",
            tags=list(d.get("tags") or []),
            library_name=d.get("library_name") or "",
            gated=bool(d.get("gated")),
        )

    @property
    def chat_capable(self) -> bool:
        if self.pipeline_tag in CHAT_PIPELINE_TAGS:
            return True
        return bool(CHAT_TAG_HINTS.intersection(self.tags))


@dataclass
class HFSpace:
    id: str
    likes: int = 0
    sdk: str = ""
    tags: list = field(default_factory=list)
    title: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "HFSpace":
        card = d.get("cardData") or {}
        return cls(
            id=d.get("id", ""),
            likes=int(d.get("likes") or 0),
            sdk=d.get("sdk") or "",
            tags=list(d.get("tags") or []),
            title=card.get("title") or d.get("id", ""),
        )


def _get(session, path: str, params: dict | None = None, timeout: int = 30):
    url = f"{API_BASE}{path}"
    try:
        r = session.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    except requests.RequestException as e:
        raise HFError(f"Network error contacting Hugging Face ({url}): {e}") from e
    if r.status_code != 200:
        raise HFError(f"Hugging Face API returned {r.status_code} for {url}: {r.text[:200]}")
    try:
        return r.json()
    except ValueError as e:
        raise HFError(f"Invalid JSON from Hugging Face for {url}") from e


def _session(session):
    return session if session is not None else requests.Session()


def search_models(query: str = "", limit: int = 40, pipeline_tag: str = "text-generation",
                  sort: str = "likes", session=None) -> list[HFModel]:
    params = {"full": "true", "sort": sort, "direction": "-1", "limit": str(limit)}
    if query:
        params["search"] = query
    if pipeline_tag:
        params["pipeline_tag"] = pipeline_tag
    data = _get(_session(session), "/models", params)
    return [HFModel.from_dict(d) for d in data if d.get("id")]


def search_spaces(query: str = "", limit: int = 40, sort: str = "likes", session=None) -> list[HFSpace]:
    params = {"full": "true", "sort": sort, "direction": "-1", "limit": str(limit)}
    if query:
        params["search"] = query
    data = _get(_session(session), "/spaces", params)
    return [HFSpace.from_dict(d) for d in data if d.get("id")]


def model_details(model_id: str, session=None) -> dict:
    return _get(_session(session), f"/models/{model_id}", {"expand[]": "inferenceProviderMapping"})


def inference_providers(model_id: str, session=None) -> dict:
    details = model_details(model_id, session=session)
    ipm = details.get("inferenceProviderMapping") or {}
    return {k: v for k, v in ipm.items() if isinstance(v, dict)}


def space_url(space_id: str) -> str:
    return f"https://huggingface.co/spaces/{space_id}"


def model_url(model_id: str) -> str:
    return f"https://huggingface.co/{model_id}"
