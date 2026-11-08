from __future__ import annotations

import os
import queue
import threading

import customtkinter as ctk

from .. import agent_service, config

FONT_FAMILIES = ["Default", "Segoe UI", "Arial", "Helvetica", "Verdana", "Tahoma",
                 "Georgia", "Times New Roman", "Consolas", "Courier New"]


class SettingsDialog(ctk.CTkToplevel):
    MASK = "••••••••"

    def __init__(self, master, store, on_saved=None):
        super().__init__(master)
        self.store = store
        self.on_saved = on_saved
        self.settings = store.load_settings()
        self.title("Settings")
        self.geometry("560x560")
        self.resizable(False, False)
        self.grab_set()
        self._q: queue.Queue = queue.Queue()
        self.after(80, self._poll)

        ctk.CTkLabel(self, text="API keys", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=16, pady=(14, 4))
        self.mistral_entry = self._secret_row(
            "Mistral API key (api.mistral.ai)",
            config.resolve_mistral_key(self.settings),
            os.environ.get(config.ENV_MISTRAL_KEY) is not None,
        )
        self.hf_entry = self._secret_row(
            "Hugging Face token (router.huggingface.co)",
            config.resolve_hf_token(self.settings),
            bool(os.environ.get(config.ENV_HF_TOKEN) or os.environ.get(config.ENV_HF_TOKEN_ALT)),
        )

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(row, text="Test keys", command=self._test_keys).pack(side="left")
        ctk.CTkButton(row, text="Save", command=self._save).pack(side="left", padx=8)
        self.test_status = ctk.CTkLabel(self, text="", text_color="gray60", anchor="w", justify="left", wraplength=500)
        self.test_status.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Appearance", anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        self.appearance = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"])
        self.appearance.set(self.settings.appearance or "System")
        self.appearance.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Chat text", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(self, text="Font", anchor="w").pack(fill="x", padx=16, pady=(6, 0))
        self.font_family = ctk.CTkOptionMenu(self, values=FONT_FAMILIES)
        self.font_family.set(self.settings.chat_font_family or "Default")
        self.font_family.pack(fill="x", padx=16)
        srow = ctk.CTkFrame(self, fg_color="transparent")
        srow.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(srow, text="Text size", anchor="w").pack(side="left")
        self.font_size_label = ctk.CTkLabel(srow, text=str(int(self.settings.chat_font_size or 14)), width=30)
        self.font_size_label.pack(side="right")
        self.font_size = ctk.CTkSlider(
            self, from_=10, to=24, number_of_steps=14,
            command=lambda v: self.font_size_label.configure(text=str(int(v))),
        )
        self.font_size.set(int(self.settings.chat_font_size or 14))
        self.font_size.pack(fill="x", padx=16)

        ctk.CTkLabel(
            self,
            text="Tip: environment variables MISTRAL_API_KEY / HF_TOKEN take precedence over keys saved here. "
                 "If the keyring package is installed, saved keys go to your OS keychain.",
            text_color="gray60", wraplength=500, justify="left",
        ).pack(fill="x", padx=16, pady=10)

    def _secret_row(self, label: str, current: str, from_env: bool) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        entry = ctk.CTkEntry(self, show="•")
        if from_env:
            entry.configure(placeholder_text="set via environment variable (takes precedence)")
            source = "source: environment variable (overrides saved key)"
        elif current:
            entry.insert(0, self.MASK)
            source = "source: saved locally"
        else:
            source = "source: not set"
        entry.pack(fill="x", padx=16)
        ctk.CTkLabel(self, text=source, anchor="w", text_color="gray60",
                     font=ctk.CTkFont(size=11)).pack(fill="x", padx=16)
        return entry

    def _entry_secret(self, entry: ctk.CTkEntry, resolved: str) -> str:
        value = entry.get()
        if value and value != self.MASK:
            return value
        return resolved

    def _test_keys(self) -> None:
        mk = self._entry_secret(self.mistral_entry, config.resolve_mistral_key(self.settings))
        hk = self._entry_secret(self.hf_entry, config.resolve_hf_token(self.settings))
        self.test_status.configure(text="Testing…")
        threading.Thread(target=self._test_worker, args=(mk, hk), daemon=True).start()

    def _test_worker(self, mistral_key: str, hf_token: str) -> None:
        results = []
        try:
            if mistral_key:
                results.append(agent_service.test_mistral_key(mistral_key))
            if hf_token:
                results.append(agent_service.test_hf_token(hf_token))
        except Exception as e:
            results.append(f"test error: {e}")
        if not results:
            results.append("No keys entered.")
        self._q.put(("test", "\n".join(results)))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "test":
                    self.test_status.configure(text=payload)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(80, self._poll)

    def _save(self) -> None:
        s = self.settings
        mv = self.mistral_entry.get()
        if mv and mv != self.MASK:
            config.persist_secret(s, "mistral_api_key", mv)
        hv = self.hf_entry.get()
        if hv and hv != self.MASK:
            config.persist_secret(s, "hf_token", hv)
        s.appearance = self.appearance.get()
        s.chat_font_family = self.font_family.get()
        s.chat_font_size = int(self.font_size.get())
        self.store.save_settings(s)
        if self.on_saved:
            self.on_saved()
        self.destroy()
