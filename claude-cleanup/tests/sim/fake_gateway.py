"""假的 Anthropic 兼容网关：只在本机监听，回固定内容，把收到的请求记到日志里。"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
DUMP = sys.argv[3] if len(sys.argv) > 3 else ""  # 给了目录就把每个请求体存下来


def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def reply(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        with open(LOG, "a") as f:
            f.write(f"GET {self.path}\n")
        self.reply(404, {"type": "error", "error": {"type": "not_found_error", "message": "not found"}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        auth = self.headers.get("Authorization", "") or self.headers.get("x-api-key", "")
        with open(LOG, "a") as f:
            f.write(f"POST {self.path} model={body.get('model')} stream={body.get('stream')} tools={len(body.get('tools') or [])} "
                    f"auth={'yes' if auth else 'no'} beta={self.headers.get('anthropic-beta', '')}\n")
        tokens = max(1, len(json.dumps(body)) // 4)
        if DUMP:
            import os, time
            with open(os.path.join(DUMP, f"{time.time():.6f}{self.path.split('?')[0].replace('/', '_')}.json"), "w") as f:
                json.dump(body, f, ensure_ascii=False)
        if self.path.startswith("/v1/messages/count_tokens"):
            return self.reply(200, {"input_tokens": tokens})
        if not self.path.startswith("/v1/messages"):
            return self.reply(404, {"type": "error", "error": {"type": "not_found_error", "message": "not found"}})
        model = body.get("model", "claude-fake")
        message = {"id": "msg_fake", "type": "message", "role": "assistant", "model": model, "content": [],
                   "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": tokens, "output_tokens": 1}}
        if not body.get("stream"):
            message.update(content=[{"type": "text", "text": "好"}], stop_reason="end_turn")
            return self.reply(200, message)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(sse("message_start", {"type": "message_start", "message": message}))
        self.wfile.write(sse("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}))
        self.wfile.write(sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "好"}}))
        self.wfile.write(sse("content_block_stop", {"type": "content_block_stop", "index": 0}))
        self.wfile.write(sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 1}}))
        self.wfile.write(sse("message_stop", {"type": "message_stop"}))


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
