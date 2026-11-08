import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mistral_desktop.config import Settings  # noqa: E402
from mistral_desktop.store import Store  # noqa: E402
from tests.mock_server import MockHandler  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def mock_server():
    MockHandler.last_payload = None
    MockHandler.last_auth = None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}/v1"
    srv.shutdown()
    srv.server_close()
