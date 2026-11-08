from __future__ import annotations

import queue
import threading

import customtkinter as ctk

from .. import hf_api
from ..agent_service import next_color
from ..config import resolve_mistral_key
from ..models import Agent, new_id
from ..providers import OpenAICompatProvider, ProviderError, mistral_provider


class AddAgentDialog(ctk.CTkToplevel):
    def __init__(self, master, store, settings, on_saved):
        super().__init__(master)
        self.store = store
        self.settings = settings
        self.on_saved = on_saved
        self.title("Add agent")
        self.geometry("660x600")
        self.resizable(True, True)
        self.grab_set()
        self._q: queue.Queue = queue.Queue()
        self._selected = None
        self._mode = "model"
        self.after(80, self._poll)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_mistral = tabs.add("Mistral")
        self.tab_hf = tabs.add("Hugging Face")
        self.tab_custom = tabs.add("Custom endpoint")
        self._build_mistral_tab()
        self._build_hf_tab()
        self._build_custom_tab()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._q.get_nowait()
                self._handle(kind, payload)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(80, self._poll)

    def _handle(self, kind, payload) -> None:
        if kind == "mistral_models":
            self.mistral_model.configure(values=payload)
            if payload:
                self.mistral_model.set(payload[0])
            self.mistral_status.configure(text=f"{len(payload)} models")
        elif kind == "mistral_error":
            self.mistral_status.configure(text=payload)
        elif kind == "hf_results":
            mode, items = payload
            self._render_hf_results(mode, items)
        elif kind == "hf_error":
            self.hf_status.configure(text=payload)
        elif kind == "hf_ipm":
            if payload:
                names = ", ".join(sorted(payload))[:90]
                self.hf_warn.configure(text=f"Runnable on HF Inference Providers via: {names}")
            else:
                self.hf_warn.configure(
                    text="Not listed on HF Inference Providers — chat may fail unless the model is deployed elsewhere."
                )
        elif kind == "custom_test":
            self.custom_status.configure(text=payload)

    def _build_mistral_tab(self) -> None:
        t = self.tab_mistral
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(row, text="Fetch Mistral models", command=self._fetch_mistral_models).pack(side="left")
        self.mistral_status = ctk.CTkLabel(row, text="", text_color="gray60")
        self.mistral_status.pack(side="left", padx=10)
        ctk.CTkLabel(t, text="Model", anchor="w").pack(fill="x", padx=10)
        self.mistral_model = ctk.CTkComboBox(t, values=[])
        self.mistral_model.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(t, text="Name", anchor="w").pack(fill="x", padx=10)
        self.mistral_name = ctk.CTkEntry(t)
        self.mistral_name.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(t, text="System prompt (optional)", anchor="w").pack(fill="x", padx=10)
        self.mistral_prompt = ctk.CTkTextbox(t, height=70)
        self.mistral_prompt.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(t, text="Add agent", command=self._add_mistral).pack(pady=8)

    def _fetch_mistral_models(self) -> None:
        key = resolve_mistral_key(self.settings)
        if not key:
            self.mistral_status.configure(text="Set MISTRAL_API_KEY in Settings (⚙) first.")
            return
        self.mistral_status.configure(text="Fetching…")
        threading.Thread(target=self._fetch_models_worker, args=(key,), daemon=True).start()

    def _fetch_models_worker(self, key: str) -> None:
        try:
            models = mistral_provider(key).list_models()
            self._q.put(("mistral_models", [m["id"] for m in models]))
        except ProviderError as e:
            self._q.put(("mistral_error", str(e)))

    def _add_mistral(self) -> None:
        model = self.mistral_model.get().strip()
        if not model:
            self.mistral_status.configure(text="Pick or type a model id.")
            return
        agent = Agent(
            id=new_id(),
            name=self.mistral_name.get().strip() or model,
            provider="mistral",
            model=model,
            system_prompt=self.mistral_prompt.get("1.0", "end").strip(),
            source="mistral",
            color=next_color(self.store.list_agents()),
        )
        self.store.save_agent(agent)
        self.on_saved(agent)
        self.destroy()

    def _build_hf_tab(self) -> None:
        t = self.tab_hf
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=8)
        self.hf_query = ctk.CTkEntry(row, placeholder_text="Search Hugging Face (e.g. qwen, llama, agent)…")
        self.hf_query.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.hf_query.bind("<Return>", lambda e: self._hf_search("model"))
        ctk.CTkButton(row, text="Models", width=80, command=lambda: self._hf_search("model")).pack(side="left", padx=2)
        ctk.CTkButton(row, text="Spaces", width=80, command=lambda: self._hf_search("space")).pack(side="left", padx=2)
        opts = ctk.CTkFrame(t, fg_color="transparent")
        opts.pack(fill="x", padx=10)
        self.hf_chat_only = ctk.CTkCheckBox(opts, text="Chat-capable models only")
        self.hf_chat_only.select()
        self.hf_chat_only.pack(side="left")
        self.hf_status = ctk.CTkLabel(opts, text="", text_color="gray60")
        self.hf_status.pack(side="left", padx=10)
        self.hf_results = ctk.CTkScrollableFrame(t, height=190)
        self.hf_results.pack(fill="both", expand=True, padx=10, pady=6)
        self.hf_selected_label = ctk.CTkLabel(t, text="Selected: —", anchor="w")
        self.hf_selected_label.pack(fill="x", padx=10)
        ctk.CTkLabel(t, text="Name", anchor="w").pack(fill="x", padx=10, pady=(6, 0))
        self.hf_name = ctk.CTkEntry(t)
        self.hf_name.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(t, text="System prompt (optional, models only)", anchor="w").pack(fill="x", padx=10)
        self.hf_prompt = ctk.CTkTextbox(t, height=56)
        self.hf_prompt.pack(fill="x", padx=10, pady=(0, 4))
        self.hf_warn = ctk.CTkLabel(t, text="", text_color="#d19a66", anchor="w", wraplength=600, justify="left")
        self.hf_warn.pack(fill="x", padx=10)
        ctk.CTkButton(t, text="Add agent", command=self._add_hf).pack(pady=6)

    def _hf_search(self, mode: str) -> None:
        q = self.hf_query.get().strip()
        self.hf_status.configure(text="Searching…")
        threading.Thread(target=self._hf_worker, args=(mode, q), daemon=True).start()

    def _hf_worker(self, mode: str, q: str) -> None:
        try:
            if mode == "space":
                items = hf_api.search_spaces(q, limit=30)
            else:
                tag = "text-generation" if self.hf_chat_only.get() else ""
                items = hf_api.search_models(q, limit=30, pipeline_tag=tag)
            self._q.put(("hf_results", (mode, items)))
        except hf_api.HFError as e:
            self._q.put(("hf_error", str(e)))

    def _render_hf_results(self, mode: str, items: list) -> None:
        self._mode = mode
        for w in self.hf_results.winfo_children():
            w.destroy()
        self.hf_status.configure(text=f"{len(items)} results")
        if not items:
            return
        for item in items:
            if mode == "space":
                text = f"{item.id}   ♥ {item.likes}   [{item.sdk}]"
            else:
                text = f"{item.id}   ♥ {item.likes}   ⬇ {item.downloads}"
            btn = ctk.CTkButton(
                self.hf_results, text=text, anchor="w", fg_color="transparent",
                command=lambda it=item: self._select_hf(mode, it),
            )
            btn.pack(fill="x", pady=1)

    def _select_hf(self, mode: str, item) -> None:
        self._selected = (mode, item)
        self.hf_selected_label.configure(text=f"Selected: {item.id}")
        self.hf_name.delete(0, "end")
        self.hf_name.insert(0, item.id.split("/")[-1])
        self.hf_warn.configure(text="")
        if mode == "model":
            threading.Thread(target=self._ipm_worker, args=(item.id,), daemon=True).start()

    def _ipm_worker(self, model_id: str) -> None:
        try:
            self._q.put(("hf_ipm", hf_api.inference_providers(model_id)))
        except hf_api.HFError:
            self._q.put(("hf_ipm", {}))

    def _add_hf(self) -> None:
        if self._selected is None:
            self.hf_status.configure(text="Select a result first.")
            return
        mode, item = self._selected
        name = self.hf_name.get().strip() or item.id
        if mode == "space":
            agent = Agent(
                id=new_id(), name=name, provider="huggingface_space", model=item.id,
                space_id=item.id, source="huggingface_space",
                color=next_color(self.store.list_agents()),
            )
        else:
            agent = Agent(
                id=new_id(), name=name, provider="huggingface", model=item.id,
                system_prompt=self.hf_prompt.get("1.0", "end").strip(),
                source="huggingface_model", color=next_color(self.store.list_agents()),
            )
        self.store.save_agent(agent)
        self.on_saved(agent)
        self.destroy()

    def _build_custom_tab(self) -> None:
        t = self.tab_custom
        self.custom_entries = {}
        fields = [
            ("Name", "my-agent"),
            ("Base URL", "http://localhost:11434/v1"),
            ("Model", "llama3.1"),
            ("API key (optional)", ""),
        ]
        for label, placeholder in fields:
            ctk.CTkLabel(t, text=label, anchor="w").pack(fill="x", padx=10, pady=(8, 0))
            e = ctk.CTkEntry(t, placeholder_text=placeholder)
            if label.startswith("API key"):
                e.configure(show="•")
            e.pack(fill="x", padx=10)
            self.custom_entries[label] = e
        ctk.CTkLabel(t, text="System prompt (optional)", anchor="w").pack(fill="x", padx=10, pady=(8, 0))
        self.custom_prompt = ctk.CTkTextbox(t, height=56)
        self.custom_prompt.pack(fill="x", padx=10, pady=(0, 8))
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(row, text="Test connection", command=self._test_custom).pack(side="left")
        self.custom_status = ctk.CTkLabel(row, text="", text_color="gray60")
        self.custom_status.pack(side="left", padx=10)
        ctk.CTkButton(t, text="Add agent", command=self._add_custom).pack(pady=8)

    def _test_custom(self) -> None:
        base = self.custom_entries["Base URL"].get().strip()
        key = self.custom_entries["API key (optional)"].get().strip()
        if not base:
            self.custom_status.configure(text="Base URL is required.")
            return
        self.custom_status.configure(text="Testing…")
        threading.Thread(target=self._test_worker, args=(base, key), daemon=True).start()

    def _test_worker(self, base: str, key: str) -> None:
        try:
            models = OpenAICompatProvider(base, key).list_models()
            self._q.put(("custom_test", f"OK — {len(models)} models visible"))
        except ProviderError as e:
            self._q.put(("custom_test", str(e)))

    def _add_custom(self) -> None:
        base = self.custom_entries["Base URL"].get().strip()
        model = self.custom_entries["Model"].get().strip()
        if not (base and model):
            self.custom_status.configure(text="Base URL and model are required.")
            return
        agent = Agent(
            id=new_id(),
            name=self.custom_entries["Name"].get().strip() or model,
            provider="openai_compatible",
            model=model,
            base_url=base,
            api_key=self.custom_entries["API key (optional)"].get().strip(),
            system_prompt=self.custom_prompt.get("1.0", "end").strip(),
            source="custom",
            color=next_color(self.store.list_agents()),
        )
        self.store.save_agent(agent)
        self.on_saved(agent)
        self.destroy()
