from __future__ import annotations

import argparse
import sys

from .agent_service import run_chat, seed_default_agents
from .config import default_data_dir
from .models import Message
from .store import Store


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mistral-desktop",
        description="Desktop app for chatting with Mistral and with agents added from "
                    "Hugging Face or any custom OpenAI-compatible endpoint.",
    )
    p.add_argument("--data-dir", default=None, help="Override the data/config directory.")
    p.add_argument("--list-agents", action="store_true", help="List saved agents and exit.")
    p.add_argument("--agent", default=None, help="Agent id or name to use in CLI mode.")
    p.add_argument("--cli", nargs="?", const="", default=None, metavar="PROMPT",
                   help="Headless mode: chat in the terminal (optionally with a one-shot PROMPT).")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    store = Store(args.data_dir or default_data_dir())
    seed_default_agents(store)
    if args.list_agents:
        for a in store.list_agents():
            print(f"{a.id}  {a.provider:<18} {a.model:<40} {a.name}")
        return 0
    if args.cli is not None:
        return _cli(store, args)
    from .app import run_app

    run_app(store)
    return 0


def _cli(store: Store, args) -> int:
    agents = store.list_agents()
    if not agents:
        print("No agents saved yet — start the GUI once to add some.", file=sys.stderr)
        return 1
    agent = store.find_agent(args.agent) if args.agent else None
    if args.agent and agent is None:
        print(f"No agent matching {args.agent!r}", file=sys.stderr)
        return 1
    agent = agent or agents[0]
    settings = store.load_settings()
    conv = store.load_conversation(agent.id)

    def exchange(text: str) -> None:
        conv.messages.append(Message(role="user", content=text))
        msgs = [m.to_api() for m in conv.messages]
        parts = []
        try:
            for chunk in run_chat(agent, settings, msgs):
                if chunk.text:
                    parts.append(chunk.text)
                    sys.stdout.write(chunk.text)
                    sys.stdout.flush()
            print()
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            conv.messages.pop()
            store.save_conversation(conv)
            return
        conv.messages.append(Message(role="assistant", content="".join(parts)))
        store.save_conversation(conv)

    if args.cli:
        exchange(args.cli)
        return 0
    print(f"Chatting with {agent.name} ({agent.provider} · {agent.model}). Type 'exit' to quit.")
    while True:
        try:
            line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in {"exit", "quit"}:
            return 0
        if line.strip():
            exchange(line.strip())
