# Mistral Desktop

A desktop app (Python + customtkinter) for chatting with **Mistral** models and with **agents you add
from Hugging Face** — plus any other OpenAI-compatible endpoint ("and more": Ollama, LM Studio,
OpenRouter, Together, vLLM, …).

## Features

- **Agents sidebar** — every agent you add appears in the sidebar with its own chat history
  (persisted locally per agent).
- **Add agents from three sources** ("＋ Add agent"):
  - **Mistral** — fetch the model catalog from `api.mistral.ai` with your API key and add any model
    (defaults `mistral-large-latest` / `mistral-small-latest` are pre-seeded).
  - **Hugging Face** — search HF **models** (chat-capable filter, shows ♥ likes / ⬇ downloads and
    whether the model is runnable via HF Inference Providers) and add them; they chat through
    `router.huggingface.co/v1` with your HF token. Also search HF **Spaces** (agent demos such as
    `smolagents/computer-agent`) and add them as one-click cards that open on huggingface.co.
  - **Custom endpoint** — any OpenAI-compatible base URL + model + optional API key, with a
    "Test connection" button. Examples below.
- **Streaming chat UI** — token-by-token rendering, Enter to send / Shift+Enter for newline,
  per-agent system prompts, change model inline, clear chat, right-click an agent to delete it.
- **Settings** — Mistral API key, HF token, light/dark theme. Keys are read from env vars first
  (`MISTRAL_API_KEY`, `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN`), then the OS keychain if `keyring`
  is installed, then a local `settings.json` (mode `0600`).
- **Headless CLI mode** for scripting/testing.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export MISTRAL_API_KEY=...        # from https://console.mistral.ai
python -m mistral_desktop         # or: python main.py
```

Then open **⚙ Settings** (or export `HF_TOKEN=...` at huggingface.co/settings/tokens) and use
**＋ Add agent → Hugging Face** to search and add HF models/spaces.

## Custom endpoints ("and more")

| Service | Base URL | API key |
|---|---|---|
| Ollama (local) | `http://localhost:11434/v1` | optional |
| LM Studio (local) | `http://localhost:1234/v1` | optional |
| OpenRouter | `https://openrouter.ai/api/v1` | required |
| Together AI | `https://api.together.xyz/v1` | required |
| vLLM / text-generation-webui | `http://<host>:<port>/v1` | optional |

## CLI mode

```bash
python -m mistral_desktop --list-agents
python -m mistral_desktop --cli "Explain LoRA in one sentence" --agent "Mistral Small"
python -m mistral_desktop --cli            # interactive REPL with the first agent
```

## Data & config

- Linux: `~/.config/mistral-desktop/` · macOS: `~/Library/Application Support/MistralDesktop/` ·
  Windows: `%APPDATA%\MistralDesktop/`
- Override with `--data-dir PATH` or `MISTRAL_DESKTOP_HOME=/path`.
- Contents: `agents.json`, `settings.json` (both `0600`), `conversations/<agent_id>.json`.

## Development

```bash
pip install -r requirements-dev.txt
pytest                 # offline tests; providers are tested against a loopback mock server
python -m compileall mistral_desktop
```

## Packaging (single-file desktop binary)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Mistral Desktop" main.py
```

## Architecture

```
mistral_desktop/
  main.py               CLI + GUI entry point
  app.py                GUI bootstrap (customtkinter, imported lazily)
  config.py             paths, settings, secret resolution (env > keyring > file)
  models.py             Agent / Message / Conversation dataclasses
  store.py              JSON persistence under the per-user data dir
  hf_api.py             Hugging Face REST client (models, spaces, inference providers)
  agent_service.py      seeding, provider resolution, chat orchestration
  providers/            OpenAI-compatible streaming chat client (+ Mistral / HF presets)
  ui/                   main window, chat view, add-agent dialog, settings dialog
tests/                  pytest suite (store, hf_api parsing, providers vs loopback server, CLI e2e)
```

All chat traffic goes over the providers' OpenAI-compatible `…/v1/chat/completions` endpoints with
SSE streaming: Mistral (`https://api.mistral.ai/v1`), Hugging Face Inference Providers
(`https://router.huggingface.co/v1`), or any custom base URL.
