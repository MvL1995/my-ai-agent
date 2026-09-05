import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from workflow_entry import execute_workflow_request
from workflow_history import get_workflow_history, get_workflow_run


HOST = "127.0.0.1"
PORT = 8000
MAX_BODY_BYTES = 64_000
INDEX_PATH = Path(__file__).resolve().parent / "web" / "index.html"
TOKENS_PATH = Path(__file__).resolve().parent / "tokens.css"


def build_request_handler(
    handlers,
    execute_workflow=execute_workflow_request,
    list_runs=get_workflow_history,
    read_run=get_workflow_run,
    index_path=INDEX_PATH,
    tokens_path=TOKENS_PATH,
):
    class RequestHandler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/":
                try:
                    body = Path(index_path).read_bytes()
                except OSError:
                    self.send_json(500, {"error": "Web interface unavailable."})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/tokens.css":
                try:
                    body = Path(tokens_path).read_bytes()
                except OSError:
                    self.send_json(500, {"error": "Stylesheet unavailable."})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/api/workflows":
                self.send_json(200, {"runs": list_runs(limit=10)})
                return

            prefix = "/api/workflows/"
            if path.startswith(prefix):
                workflow_id = unquote(path[len(prefix):]).strip()
                if not workflow_id:
                    self.send_json(400, {"error": "workflow_id cannot be empty."})
                    return

                record = read_run(workflow_id)
                if record is None:
                    self.send_json(404, {"error": "Workflow not found."})
                    return

                self.send_json(200, record)
                return

            self.send_json(404, {"error": "Not found."})

        def do_POST(self):
            if urlparse(self.path).path != "/api/workflows":
                self.send_json(404, {"error": "Not found."})
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_json(400, {"error": "Invalid Content-Length."})
                return

            if content_length <= 0 or content_length > MAX_BODY_BYTES:
                self.send_json(400, {"error": "Invalid request size."})
                return

            try:
                payload = json.loads(
                    self.rfile.read(content_length).decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_json(400, {"error": "Invalid JSON."})
                return

            if not isinstance(payload, dict):
                self.send_json(400, {"error": "JSON body must be an object."})
                return

            values = {}
            for field in ("objective", "context"):
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.send_json(400, {"error": f"{field} cannot be empty."})
                    return
                values[field] = value.strip()

            command = f"客户项目：{values['objective']} | {values['context']}"

            try:
                result = execute_workflow(command, handlers)
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
                return
            except Exception:
                self.send_json(500, {"error": "Workflow execution failed."})
                return

            self.send_json(200, asdict(result))

        def log_message(self, format, *args):
            return

    return RequestHandler


def run_server(host=HOST, port=PORT):
    from main import task_handlers

    server = HTTPServer(
        (host, port),
        build_request_handler(task_handlers),
    )
    print(f"AI Agency Operator: http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
