from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "mistral-desktop"
ENV_MISTRAL_KEY = "MISTRAL_API_KEY"
ENV_HF_TOKEN = "HF_TOKEN"
ENV_HF_TOKEN_ALT = "HUGGING_FACE_HUB_TOKEN"
KEYRING_SERVICE = "mistral-desktop"


def default_data_dir() -> Path:
    override = os.environ.get("MISTRAL_DESKTOP_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "MistralDesktop"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MistralDesktop"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


@dataclass
class Settings:
    mistral_api_key: str = ""
    hf_token: str = ""
    appearance: str = "System"
    last_agent_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "Settings":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


def _keyring():
    try:
        import keyring

        return keyring
    except Exception:
        return None


def resolve_mistral_key(settings: Settings) -> str:
    kr = _keyring()
    return (
        os.environ.get(ENV_MISTRAL_KEY)
        or settings.mistral_api_key
        or (kr.get_password(KEYRING_SERVICE, "mistral_api_key") if kr else "")
        or ""
    )


def resolve_hf_token(settings: Settings) -> str:
    kr = _keyring()
    return (
        os.environ.get(ENV_HF_TOKEN)
        or os.environ.get(ENV_HF_TOKEN_ALT)
        or settings.hf_token
        or (kr.get_password(KEYRING_SERVICE, "hf_token") if kr else "")
        or ""
    )


def persist_secret(settings: Settings, field: str, value: str) -> None:
    kr = _keyring()
    if kr is not None:
        if value:
            kr.set_password(KEYRING_SERVICE, field, value)
        else:
            try:
                kr.delete_password(KEYRING_SERVICE, field)
            except Exception:
                pass
        setattr(settings, field, "")
    else:
        setattr(settings, field, value)
