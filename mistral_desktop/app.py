from __future__ import annotations

from .store import Store


def run_app(store: Store) -> None:
    import customtkinter as ctk

    settings = store.load_settings()
    ctk.set_default_color_theme("blue")
    ctk.set_appearance_mode(settings.appearance or "System")

    from .ui.main_window import MainWindow

    app = MainWindow(store)
    app.mainloop()
