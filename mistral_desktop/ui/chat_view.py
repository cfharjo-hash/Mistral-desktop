from __future__ import annotations

import math
import time
from pathlib import Path

import customtkinter as ctk

from ..files import read_file_block

ROLE_LABELS = {"user": "You", "assistant": "Assistant", "system": "System"}
ROLE_COLORS = {
    "user": ("#3b6fb4", "#2c4f80"),
    "assistant": ("gray88", "gray17"),
    "system": ("#b04040", "#7a2e2e"),
}
BASE_SIZE = 14


class MessageBubble(ctk.CTkFrame):
    def __init__(self, master, role: str, content: str = "", width_hint: int = 620,
                 font_family=None, font_size: int = BASE_SIZE):
        super().__init__(master, corner_radius=10, fg_color=ROLE_COLORS.get(role, ROLE_COLORS["assistant"]))
        self.role = role
        self._content = ""
        self._width_hint = width_hint
        self.font_family = font_family
        self.font_size = font_size
        self.header_font = ctk.CTkFont(size=max(10, font_size - 3), weight="bold", family=font_family)
        self.body_font = ctk.CTkFont(size=font_size, family=font_family)
        self.header = ctk.CTkLabel(
            self,
            text=f"{ROLE_LABELS.get(role, role)}  ·  {time.strftime('%H:%M')}",
            font=self.header_font,
            anchor="w",
        )
        self.header.pack(fill="x", padx=10, pady=(6, 0))
        self.text = ctk.CTkTextbox(
            self, wrap="word", activate_scrollbars=False, border_width=0,
            fg_color="transparent", height=32, font=self.body_font,
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self.set_text(content)
        self.text.configure(state="disabled")

    def set_font(self, font_family, font_size: int) -> None:
        self.font_family = font_family
        self.font_size = font_size
        self.header_font = ctk.CTkFont(size=max(10, font_size - 3), weight="bold", family=font_family)
        self.body_font = ctk.CTkFont(size=font_size, family=font_family)
        self.header.configure(font=self.header_font)
        self.text.configure(font=self.body_font)
        self._refit()

    def set_text(self, content: str) -> None:
        self._content = content
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")
        self._refit()

    def append(self, delta: str) -> None:
        self.set_text(self._content + delta)

    def _refit(self) -> None:
        w = self.text.winfo_width()
        if w <= 1:
            w = self._width_hint
        scale = self.font_size / BASE_SIZE
        cpl = max(24, int((w - 24) / (7.2 * scale)))
        lines = 0
        for seg in self._content.split("\n"):
            lines += max(1, math.ceil(len(seg) / cpl))
        self.text.configure(height=min(700, max(30, int(lines * 19 * scale) + 14)))


class ChatView(ctk.CTkFrame):
    def __init__(self, master, on_send, font_family=None, font_size: int = BASE_SIZE):
        super().__init__(master)
        self.on_send = on_send
        self._busy = False
        self._stream_bubble = None
        self.font_family = font_family
        self.font_size = font_size
        self.messages_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.messages_frame.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        composer = ctk.CTkFrame(self)
        composer.pack(fill="x", padx=8, pady=8)
        self.entry = ctk.CTkTextbox(composer, height=64, wrap="word",
                                    font=ctk.CTkFont(size=font_size, family=font_family))
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=6)
        self.entry.bind("<Return>", self._on_return)
        self.attach_label = ctk.CTkLabel(composer, text="", text_color="gray60",
                                         font=ctk.CTkFont(size=11), anchor="e")
        self.attach_label.pack(side="right", padx=(0, 6), pady=6)
        self.send_btn = ctk.CTkButton(composer, text="Send", width=90, command=self._send)
        self.send_btn.pack(side="right", pady=6)
        self._attachments = []
        self._setup_dnd()

    def apply_text_style(self, font_family, font_size: int) -> None:
        self.font_family = font_family
        self.font_size = font_size
        self.entry.configure(font=ctk.CTkFont(size=font_size, family=font_family))
        for w in self.messages_frame.winfo_children():
            if isinstance(w, MessageBubble):
                w.set_font(font_family, font_size)

    def _setup_dnd(self) -> None:
        self._dnd = False
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD

            if hasattr(TkinterDnD, "_require"):
                TkinterDnD._require(self)
            else:
                self.tk.call("package", "require", "tkdnd")
            for w in (self.entry, self):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
            self._dnd = True
        except Exception:
            self._dnd = False

    def _on_drop(self, event):
        try:
            paths = list(self.tk.splitlist(event.data))
        except Exception:
            paths = []
        if paths:
            self.add_dropped_files(paths)
        return "break"

    def add_dropped_files(self, paths: list) -> None:
        blocks = []
        for p in paths:
            blocks.append(read_file_block(p))
            self._attachments.append(Path(p).name)
        if not blocks:
            return
        current = self.entry.get("1.0", "end").rstrip("\n")
        text = (current + "\n\n" if current else "") + "\n\n".join(blocks) + "\n"
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", text)
        self.attach_label.configure(text="📎 " + ", ".join(self._attachments[-8:]))

    def _on_return(self, event):
        if not (event.state & 0x1):
            self._send()
            return "break"
        return None

    def _send(self) -> None:
        if self._busy:
            return
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return
        self.entry.delete("1.0", "end")
        self._attachments = []
        self.attach_label.configure(text="")
        self.on_send(text)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_btn.configure(state="disabled" if busy else "normal")
        self.entry.configure(state="disabled" if busy else "normal")

    def clear(self) -> None:
        for w in self.messages_frame.winfo_children():
            w.destroy()
        self._stream_bubble = None

    def show_placeholder(self, text: str = "Select an agent to start chatting.") -> None:
        self.clear()
        ctk.CTkLabel(self.messages_frame, text=text, text_color="gray60", wraplength=480).pack(pady=40, padx=20)

    def add_message(self, role: str, content: str) -> MessageBubble:
        self._drop_placeholder()
        bubble = MessageBubble(self.messages_frame, role, content,
                               font_family=self.font_family, font_size=self.font_size)
        bubble.pack(fill="x", pady=6, padx=4)
        self._scroll_bottom()
        return bubble

    def begin_stream(self) -> MessageBubble:
        self._drop_placeholder()
        self._stream_bubble = MessageBubble(self.messages_frame, "assistant", "",
                                            font_family=self.font_family, font_size=self.font_size)
        self._stream_bubble.pack(fill="x", pady=6, padx=4)
        return self._stream_bubble

    def append_delta(self, delta: str) -> None:
        if self._stream_bubble is not None:
            self._stream_bubble.append(delta)
            self._scroll_bottom()

    def end_stream(self, full_text: str) -> None:
        if self._stream_bubble is not None:
            self._stream_bubble.set_text(full_text)
            self._stream_bubble = None
        self._scroll_bottom()

    def show_error(self, message: str) -> None:
        self.add_message("system", f"Error: {message}")

    def _drop_placeholder(self) -> None:
        for w in self.messages_frame.winfo_children():
            if isinstance(w, ctk.CTkLabel):
                w.destroy()

    def _scroll_bottom(self) -> None:
        try:
            self.messages_frame.update_idletasks()
            self.messages_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass
