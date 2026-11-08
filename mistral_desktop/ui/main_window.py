from __future__ import annotations

import queue
import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from .. import hf_api
from ..agent_service import run_chat
from ..models import Conversation, Message
from ..store import Store
from .add_agent_dialog import AddAgentDialog
from .chat_view import ChatView
from .settings_dialog import SettingsDialog


class MainWindow(ctk.CTk):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.settings = store.load_settings()
        self.title("Mistral Desktop")
        self.geometry("1080x680")
        self.minsize(820, 480)
        self._q: queue.Queue = queue.Queue()
        self._agent = None
        self._streaming = False
        self._menu = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        head = ctk.CTkFrame(sidebar, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=(12, 4))
        ctk.CTkLabel(head, text="Mistral Desktop", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="＋", width=32, command=self._open_add_dialog).pack(side="right")

        self.agent_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.agent_frame.pack(fill="both", expand=True, padx=6, pady=4)

        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(bottom, text="＋ Add agent", command=self._open_add_dialog).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(bottom, text="⚙ Settings", fg_color="transparent", border_width=1,
                      command=self._open_settings).pack(fill="x")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=6)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(main)
        topbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.name_label = ctk.CTkLabel(topbar, text="No agent selected",
                                       font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
        self.name_label.pack(side="left", padx=10, pady=8)
        self.badge = ctk.CTkLabel(topbar, text="", font=ctk.CTkFont(size=11), text_color="gray60", anchor="w")
        self.badge.pack(side="left", padx=(6, 0), pady=8)
        self.model_btn = ctk.CTkButton(topbar, text="Change model", width=110, command=self._change_model)
        self.model_btn.pack(side="right", padx=6, pady=6)
        self.space_btn = ctk.CTkButton(topbar, text="Open Space ↗", width=110, state="disabled",
                                       command=lambda: self._open_space())
        self.space_btn.pack(side="right", padx=6, pady=6)
        self.clear_btn = ctk.CTkButton(topbar, text="Clear chat", width=90, command=self._clear_chat)
        self.clear_btn.pack(side="right", padx=6, pady=6)

        self.chat_view = ChatView(main, on_send=self._on_send)
        self.chat_view.grid(row=1, column=0, sticky="nsew")

        agents = self.store.list_agents()
        initial = self.store.get_agent(self.settings.last_agent_id) if self.settings.last_agent_id else None
        self.select_agent(initial or (agents[0] if agents else None))
        self.after(60, self._poll)

    def refresh_agents(self) -> None:
        for w in self.agent_frame.winfo_children():
            w.destroy()
        for a in self.store.list_agents():
            selected = self._agent is not None and a.id == self._agent.id
            btn = ctk.CTkButton(
                self.agent_frame,
                text=f"● {a.name}",
                anchor="w",
                fg_color=("gray75", "gray28") if selected else "transparent",
                hover_color=("gray70", "gray30"),
                text_color=(a.color, a.color),
                command=lambda a=a: self.select_agent(a),
            )
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-3>", lambda e, a=a: self._context_menu(e, a))

    def select_agent(self, agent) -> None:
        self._agent = agent
        self.refresh_agents()
        if agent is None:
            self.name_label.configure(text="No agent selected")
            self.badge.configure(text="")
            self.space_btn.configure(state="disabled")
            self.chat_view.show_placeholder()
            return
        self.settings.last_agent_id = agent.id
        self.store.save_settings(self.settings)
        self.name_label.configure(text=agent.name)
        self.badge.configure(text=f"{agent.provider} · {agent.model}")
        self.space_btn.configure(state="normal" if agent.is_space else "disabled")
        self.chat_view.clear()
        conv = self.store.load_conversation(agent.id)
        if not conv.messages:
            if agent.is_space:
                self.chat_view.show_placeholder(
                    "This agent is a Hugging Face Space — use “Open Space ↗” to run it on huggingface.co."
                )
            else:
                self.chat_view.show_placeholder(f"Chat with {agent.name} ({agent.model}).")
        else:
            for m in conv.messages:
                self.chat_view.add_message(m.role if m.role in ("user", "assistant") else "system", m.content)

    def _on_send(self, text: str) -> None:
        agent = self._agent
        if agent is None or self._streaming:
            return
        if agent.is_space:
            self.chat_view.show_error(
                "This agent is a Hugging Face Space — open it in the browser with “Open Space ↗”."
            )
            return
        self.chat_view.add_message("user", text)
        conv = self.store.load_conversation(agent.id)
        conv.messages.append(Message(role="user", content=text))
        self.store.save_conversation(conv)
        self._streaming = True
        self.chat_view.set_busy(True)
        self.chat_view.begin_stream()
        msgs = [m.to_api() for m in conv.messages]
        threading.Thread(target=self._worker, args=(agent, msgs), daemon=True).start()

    def _worker(self, agent, msgs) -> None:
        try:
            parts = []
            for chunk in run_chat(agent, self.settings, msgs):
                if chunk.text:
                    parts.append(chunk.text)
                    self._q.put(("delta", chunk.text))
            self._q.put(("done", "".join(parts)))
        except Exception as e:
            self._q.put(("error", str(e)))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "delta":
                    self.chat_view.append_delta(payload)
                elif kind == "done":
                    self.chat_view.end_stream(payload)
                    self._finish_stream(payload)
                elif kind == "error":
                    self.chat_view.end_stream("")
                    self.chat_view.show_error(payload)
                    self._finish_stream(None)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(60, self._poll)

    def _finish_stream(self, full_text) -> None:
        self._streaming = False
        self.chat_view.set_busy(False)
        if full_text is not None and self._agent is not None:
            conv = self.store.load_conversation(self._agent.id)
            conv.messages.append(Message(role="assistant", content=full_text))
            self.store.save_conversation(conv)

    def _context_menu(self, event, agent) -> None:
        if self._menu is not None:
            try:
                self._menu.destroy()
            except Exception:
                pass
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        if agent.is_space:
            ctk.CTkButton(menu, text="Open Space ↗", width=160,
                          command=lambda: (menu.destroy(), self._open_space(agent))).pack(padx=4, pady=4)
        ctk.CTkButton(menu, text="Delete agent", width=160, fg_color="#a33333", hover_color="#c04444",
                      command=lambda: (menu.destroy(), self._delete_agent(agent))).pack(padx=4, pady=(0, 4))
        self._menu = menu
        menu.after(5000, lambda: menu.destroy() if menu.winfo_exists() else None)

    def _delete_agent(self, agent) -> None:
        if not messagebox.askyesno("Delete agent", f"Delete '{agent.name}' and its chat history?"):
            return
        self.store.delete_agent(agent.id)
        remaining = self.store.list_agents()
        self.select_agent(remaining[0] if remaining else None)

    def _open_space(self, agent=None) -> None:
        agent = agent or self._agent
        if agent is not None and agent.is_space:
            webbrowser.open(hf_api.space_url(agent.space_id or agent.model))

    def _change_model(self) -> None:
        agent = self._agent
        if agent is None or agent.is_space:
            return
        dlg = ctk.CTkInputDialog(text=f"Model id for {agent.name}:", title="Change model")
        value = (dlg.get_input() or "").strip()
        if value:
            agent.model = value
            self.store.save_agent(agent)
            self.badge.configure(text=f"{agent.provider} · {agent.model}")

    def _clear_chat(self) -> None:
        if self._agent is None:
            return
        self.store.save_conversation(Conversation(agent_id=self._agent.id, messages=[]))
        self.chat_view.show_placeholder("Chat cleared.")

    def _open_add_dialog(self) -> None:
        AddAgentDialog(self, self.store, self.settings, on_saved=self._after_agent_saved)

    def _after_agent_saved(self, agent) -> None:
        self.select_agent(agent)

    def _open_settings(self) -> None:
        SettingsDialog(self, self.store, on_saved=self._reload_settings)

    def _reload_settings(self) -> None:
        self.settings = self.store.load_settings()
        ctk.set_appearance_mode(self.settings.appearance or "System")
