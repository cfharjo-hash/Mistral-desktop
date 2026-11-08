from mistral_desktop.files import format_size, is_probably_text, read_file_block


def test_format_size():
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_text_file_block_inlined(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello world\nline two\n", encoding="utf-8")
    block = read_file_block(str(f))
    assert "[attached file: notes.txt" in block
    assert "```text" in block
    assert "hello world" in block
    assert is_probably_text(f)


def test_extensionless_text_sniffed(tmp_path):
    f = tmp_path / "README"
    f.write_text("plain text content", encoding="utf-8")
    assert is_probably_text(f)
    assert "plain text content" in read_file_block(str(f))


def test_binary_file_not_inlined(tmp_path):
    f = tmp_path / "photo.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    assert not is_probably_text(f)
    block = read_file_block(str(f))
    assert "binary/non-text" in block
    assert "```text" not in block


def test_missing_file():
    block = read_file_block("/nonexistent/nope.txt")
    assert "could not be read" in block


def test_oversize_truncated(tmp_path):
    f = tmp_path / "big.log"
    f.write_text("x" * 5000, encoding="utf-8")
    block = read_file_block(str(f), max_bytes=1000)
    assert "truncated" in block
    assert "x" * 1000 in block
    assert "x" * 1001 not in block
