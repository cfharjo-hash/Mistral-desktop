from __future__ import annotations

import os

import customtkinter as ctk

from .. import config


class SettingsDialog(ctk.CTkToplevel):
    MASK = "••••••••"

    def __init__(self, master, store, on_saved=None):
        super().__init__(master)
        self.store = store
        self.on_saved = on_saved
        self.settings = store.load_settings()
        self.title("Settings")
        self.geometry("540x380")
        self.resizable(False, False)
        self.grab_set()

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

        ctk.CTkLabel(self, text="Appearance", anchor="w").pack(fill="x", padx=16, pady=(12, 0))
        self.appearance = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"])
        self.appearance.set(self.settings.appearance or "System")
        self.appearance.pack(fill="x", padx=16)

        ctk.CTkLabel(
            self,
            text="Tip: set MISTRAL_API_KEY / HF_TOKEN environment variables instead of storing keys here. "
                 "If the keyring package is installed, saved keys go to your OS keychain.",
            text_color="gray60", wraplength=470, justify="left",
        ).pack(fill="x", padx=16, pady=10)

        ctk.CTkButton(self, text="Save", command=self._save).pack(pady=8)

    def _secret_row(self, label: str, current: str, from_env: bool) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        entry = ctk.CTkEntry(self, show="•")
        if from_env:
            entry.configure(placeholder_text="set via environment variable")
        elif current:
            entry.insert(0, self.MASK)
        entry.pack(fill="x", padx=16)
        return entry

    def _save(self) -> None:
        s = self.settings
        mv = self.mistral_entry.get()
        if mv and mv != self.MASK:
            config.persist_secret(s, "mistral_api_key", mv)
        hv = self.hf_entry.get()
        if hv and hv != self.MASK:
            config.persist_secret(s, "hf_token", hv)
        s.appearance = self.appearance.get()
        self.store.save_settings(s)
        if self.on_saved:
            self.on_saved()
        self.destroy()
