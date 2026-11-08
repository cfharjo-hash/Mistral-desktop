import json
from http.server import BaseHTTPRequestHandler

MODELS_PAYLOAD = {
    "object": "list",
    "data": [
        {"id": "mistral-large-latest", "owned_by": "mistralai"},
        {"id": "mistral-small-latest", "owned_by": "mistralai"},
    ],
}

STREAM_EVENTS = [
    {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
    {"choices": [{"delta": {"content": ", world"}, "finish_reason": None}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
]


class MockHandler(BaseHTTPRequestHandler):
    last_payload = None
    last_auth = None

    def log_message(self, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self._json(MODELS_PAYLOAD)
        else:
            self._json({"error": {"message": "not found"}}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        MockHandler.last_payload = payload
        MockHandler.last_auth = self.headers.get("Authorization")
        if self.path != "/v1/chat/completions":
            return self._json({"error": {"message": "not found"}}, 404)
        if payload.get("model") == "bad-model":
            return self._json({"error": {"message": "model not found"}}, 400)
        if MockHandler.last_auth != "Bearer secret":
            return self._json({"error": {"message": "invalid api key"}}, 401)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for obj in STREAM_EVENTS:
            self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
