from __future__ import annotations

from pathlib import Path

MAX_TEXT_BYTES = 200_000

TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".log", ".xml", ".html", ".css", ".sh",
    ".bat", ".ps1", ".c", ".cpp", ".h", ".java", ".go", ".rs", ".rb", ".php",
    ".sql", ".env", ".gitignore", ".svg", ".tex", ".rst", ".diff", ".patch",
}


def format_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTS:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def read_file_block(path_str: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
    p = Path(path_str)
    name = p.name or str(p)
    try:
        size = p.stat().st_size
    except OSError as e:
        return f"[attached file: {name} — could not be read: {e}]"
    if not is_probably_text(p):
        return (f"[attached file: {name} ({format_size(size)}) — "
                f"binary/non-text file, content not included]")
    try:
        data = p.read_bytes()[: max_bytes + 1]
    except OSError as e:
        return f"[attached file: {name} — could not be read: {e}]"
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    text = data.decode("utf-8", errors="replace")
    note = f", truncated to first {format_size(max_bytes)}" if truncated else ""
    return f"[attached file: {name} ({format_size(size)}{note})]\n```text\n{text}\n```"
