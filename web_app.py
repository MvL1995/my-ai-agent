import io
import json
import threading
import traceback
import zipfile
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from landing_page_package import parse_landing_page_package
from memory import contains_sensitive_memory
from workflow_contract import create_project_brief
from workflow_entry import execute_workflow_request
from workflow_history import (
    SENSITIVE_WORKFLOW_ERROR,
    get_retry_effectiveness,
    get_next_attempt_number,
    get_workflow_history,
    get_workflow_run,
)


HOST = "127.0.0.1"
PORT = 8000
MAX_BODY_BYTES = 64_000
MAX_OVERRIDE_REASON_LENGTH = 200
INDEX_PATH = Path(__file__).resolve().parent / "web" / "index.html"
TOKENS_PATH = Path(__file__).resolve().parent / "tokens.css"


def build_request_handler(
    handlers,
    execute_workflow=execute_workflow_request,
    list_runs=get_workflow_history,
    read_retry_metrics=get_retry_effectiveness,
    read_run=get_workflow_run,
    next_attempt_number=get_next_attempt_number,
    index_path=INDEX_PATH,
    tokens_path=TOKENS_PATH,
):
    jobs = {}
    jobs_lock = threading.Lock()

    def run_job(
        job_id, command, retry_of=None, attempt_number=1,
        override_source=None, override_reason=None,
    ):
        try:
            result = execute_workflow(
                command,
                handlers,
                retry_of=retry_of,
                attempt_number=attempt_number,
                override_source=override_source,
                override_reason=override_reason,
            )
            payload = {"job_id": job_id, **asdict(result)}
        except (ValueError, RuntimeError) as error:
            payload = {
                "job_id": job_id,
                "status": "failed",
                "error": str(error),
            }
        except Exception:
            traceback.print_exc()
            payload = {
                "job_id": job_id,
                "status": "failed",
                "error": "Workflow execution failed.",
            }

        with jobs_lock:
            jobs[job_id] = payload

    def start_job(
        command, retry_of=None, attempt_number=1,
        override_source=None, override_reason=None,
    ):
        job_id = f"job-{uuid4().hex}"
        with jobs_lock:
            jobs[job_id] = {"job_id": job_id, "status": "running"}
        threading.Thread(
            target=run_job,
            args=(job_id, command, retry_of, attempt_number, override_source, override_reason),
            daemon=True,
        ).start()
        return job_id


    class RequestHandler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def read_json(self, empty_error="Invalid request size."):
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("Invalid Content-Length.") from error
            if content_length <= 0:
                raise ValueError(empty_error)
            if content_length > MAX_BODY_BYTES:
                raise ValueError("Invalid request size.")
            try:
                payload = json.loads(
                    self.rfile.read(content_length).decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("Invalid JSON.") from error
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object.")
            return payload

        def do_GET(self):
            path = urlparse(self.path).path

            job_prefix = "/api/jobs/"
            if path.startswith(job_prefix):
                job_id = unquote(path[len(job_prefix):]).strip()
                if not job_id:
                    self.send_json(400, {"error": "job_id cannot be empty."})
                    return

                with jobs_lock:
                    job = jobs.get(job_id)
                if job is None:
                    self.send_json(404, {"error": "Job not found."})
                    return

                self.send_json(200, job)
                return

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
                self.send_json(200, {
                    "runs": list_runs(limit=10),
                    "retry_metrics": read_retry_metrics(),
                })
                return

            prefix = "/api/workflows/"
            download_suffix = "/download"
            if path.startswith(prefix) and path.endswith(download_suffix):
                workflow_id = unquote(
                    path[len(prefix):-len(download_suffix)]
                ).strip()
                if not workflow_id:
                    self.send_json(400, {"error": "workflow_id cannot be empty."})
                    return

                record = read_run(workflow_id)
                if record is None:
                    self.send_json(404, {"error": "Workflow not found."})
                    return

                try:
                    if record.get("status") != "completed":
                        raise ValueError
                    landing_page = record.get("landing_page") or {}
                    package = parse_landing_page_package(
                        json.dumps(landing_page.get("files"), ensure_ascii=False)
                    )
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, "w") as archive:
                        for name, content in package.files.items():
                            archive.writestr(name, content.encode("utf-8"))
                    body = buffer.getvalue()
                except (AttributeError, TypeError, ValueError):
                    self.send_json(
                        409,
                        {"error": "Landing page download unavailable."},
                    )
                    return
                except Exception:
                    self.send_json(500, {"error": "Download creation failed."})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="landing-page-{workflow_id}.zip"',
                )
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

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
            path = urlparse(self.path).path
            prefix = "/api/workflows/"
            retry_suffix = "/retry"
            if (
                path.startswith(prefix)
                and path.endswith(retry_suffix)
            ):
                workflow_id = unquote(
                    path[len(prefix):-len(retry_suffix)]
                ).strip()
                if not workflow_id:
                    self.send_json(
                        400,
                        {"error": "workflow_id cannot be empty."},
                    )
                    return

                record = read_run(workflow_id)
                if record is None:
                    self.send_json(404, {"error": "Workflow not found."})
                    return

                if record.get("status") != "failed":
                    self.send_json(
                        409,
                        {"error": "Only failed workflows can be retried."},
                    )
                    return

                override_source = None
                override_reason = None
                if not record.get("retry_recommended"):
                    if not record.get("policy_adjusted"):
                        self.send_json(
                            409,
                            {
                                "error": record.get("recommended_action")
                                or "Inspect the failure before retrying."
                            },
                        )
                        return

                    try:
                        payload = self.read_json("override_reason is required.")
                    except ValueError as error:
                        self.send_json(400, {"error": str(error)})
                        return

                    override_reason = payload.get("override_reason")
                    if (
                        not isinstance(override_reason, str)
                        or not override_reason.strip()
                    ):
                        self.send_json(
                            400, {"error": "override_reason is required."}
                        )
                        return
                    override_reason = override_reason.strip()
                    if len(override_reason) > MAX_OVERRIDE_REASON_LENGTH:
                        self.send_json(400, {
                            "error": (
                                "override_reason must be at most "
                                f"{MAX_OVERRIDE_REASON_LENGTH} characters."
                            ),
                        })
                        return
                    if contains_sensitive_memory(override_reason):
                        self.send_json(
                            400, {"error": SENSITIVE_WORKFLOW_ERROR}
                        )
                        return
                    override_source = record["workflow_id"]
                command = (
                    f"客户项目：{record['objective']} | {record['context']}"
                )
                root_workflow_id = (
                    record.get("retry_of") or record["workflow_id"]
                )
                attempt_number = next_attempt_number(root_workflow_id)
                # ponytail: UI blocks duplicate clicks; reserve attempts
                # in DB if concurrent clients matter.
                job_id = start_job(
                    command,
                    root_workflow_id,
                    attempt_number,
                    override_source,
                    override_reason,
                )
                self.send_json(202, {"job_id": job_id, "status": "running"})
                return

            if path != "/api/workflows":
                self.send_json(404, {"error": "Not found."})
                return

            try:
                payload = self.read_json()
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return

            try:
                brief = create_project_brief(payload)
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return

            objective = f"为「{brief.company_name}」制作客户转化型网站包"
            context = "；".join((
                f"公司名称：{brief.company_name}",
                f"目标客户：{brief.target_customer}",
                f"核心服务：{brief.core_service}",
                f"地区：{brief.region}",
                f"语言：{brief.language}",
                f"行动号召：{brief.cta}",
                f"联系方式：{brief.contact}",
            ))
            command = f"客户项目：{objective} | {context}"
            job_id = start_job(command)

            self.send_json(202, {"job_id": job_id, "status": "running"})

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
