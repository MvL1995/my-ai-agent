import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import asdict
from html.parser import HTMLParser
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from landing_page_package import LandingPagePackage
from task_contract import AgentResult
from web_app import build_request_handler
from workflow_contract import WorkflowResult


PROJECT_DIRECTORY = Path(__file__).resolve().parent


class PreviewContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.empty_state = None
        self.frame = None
        self.download_button = None
        self.diagnostics = None
        self.retry_button = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if tag == "p" and element_id == "preview-empty":
            self.empty_state = attributes
        if tag == "iframe" and element_id == "preview-frame":
            self.frame = attributes
        if tag == "button" and element_id == "download-button":
            self.download_button = attributes
        if tag == "p" and element_id == "workflow-diagnostics":
            self.diagnostics = attributes
        if tag == "button" and element_id == "retry-button":
            self.retry_button = attributes


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_DIRECTORY)
    imported = subprocess.run(
        [sys.executable, "-c", "import main; print('imported')"],
        cwd=temp_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

assert imported.returncode == 0, imported.stderr
assert imported.stdout.strip() == "imported"


def request_json(base_url, path, method="GET", payload=None):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        base_url + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))

    with response:
        return response.status, json.loads(response.read().decode("utf-8"))


def request_raw(base_url, path):
    try:
        response = urlopen(base_url + path, timeout=5)
    except HTTPError as error:
        return error.code, error.headers, error.read()

    with response:
        return response.status, response.headers, response.read()


workflow = WorkflowResult(
    workflow_id="workflow-web-test",
    workflow_type="client_project",
    status="completed",
    steps=[
        AgentResult(
            task_id="task-research",
            agent_name="Search Agent",
            status="completed",
            output="Research output",
        )
    ],
    duration_ms=12.5,
    final_output="Project output",
    landing_page=LandingPagePackage(
        files={
            "index.html": "<main>Web</main>",
            "styles.css": "main { color: black; }",
            "script.js": "",
        }
    ),
)
workflow_record = {
    **asdict(workflow),
    "objective": "Build a restaurant landing page",
    "context": "Kuala Lumpur restaurant",
    "created_at": "2026-09-05 12:00:00",
}
failed_workflow_record = {
    **workflow_record,
    "workflow_id": "workflow-failed",
    "status": "failed",
    "objective": "Retry objective",
    "context": "Retry context",
    "landing_page": None,
}
project_payload = {
    "company_name": "Alpha Studio",
    "target_customer": "Malaysian SMEs",
    "core_service": "AI websites",
    "region": "Malaysia",
    "language": "Chinese",
    "cta": "Book a consultation",
    "contact": "WhatsApp: +60123456789",
}
received_commands = []
stub_handlers = {"Search Agent": object()}
execution_gate = threading.Event()


def fake_execute(command, handlers):
    received_commands.append((command, handlers))
    if not execution_gate.wait(timeout=2):
        raise RuntimeError("Execution gate timed out.")
    return workflow


def fake_list_runs(limit=10):
    assert limit == 10
    return [
        {
            "created_at": workflow_record["created_at"],
            "workflow_id": workflow_record["workflow_id"],
            "workflow_type": workflow_record["workflow_type"],
            "status": workflow_record["status"],
            "objective": workflow_record["objective"],
        }
    ]


def fake_read_run(workflow_id):
    if workflow_id == workflow_record["workflow_id"]:
        return workflow_record
    if workflow_id == failed_workflow_record["workflow_id"]:
        return failed_workflow_record
    if workflow_id == "workflow-incomplete":
        return {
            **workflow_record,
            "workflow_id": workflow_id,
            "status": "running",
            "landing_page": None,
        }
    if workflow_id == "workflow-invalid-package":
        return {
            **workflow_record,
            "workflow_id": workflow_id,
            "landing_page": {"files": {"index.html": "<main>Web</main>"}},
        }
    return None


handler = build_request_handler(
    stub_handlers,
    execute_workflow=fake_execute,
    list_runs=fake_list_runs,
    read_run=fake_read_run,
)
server = HTTPServer(("127.0.0.1", 0), handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f"http://127.0.0.1:{server.server_port}"

try:
        with urlopen(base_url + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
        assert "AI Agency Operator" in page
        assert 'id="client-form"' in page
        for field_name in project_payload:
            assert f'name="{field_name}"' in page
        assert 'id="history-list"' in page
        preview = PreviewContractParser()
        preview.feed(page)
        assert preview.empty_state is not None
        assert preview.frame is not None
        assert preview.frame.get("sandbox") == "allow-scripts"
        assert "hidden" in preview.frame
        assert preview.download_button is not None
        assert preview.diagnostics is not None
        assert "hidden" in preview.download_button

        assert preview.retry_button is not None
        assert "hidden" in preview.retry_button
        with urlopen(base_url + "/tokens.css", timeout=5) as response:
            tokens = response.read().decode("utf-8")
        assert "--color-accent" in tokens

        release_timer = threading.Timer(0.5, execution_gate.set)
        release_timer.start()
        started_at = time.monotonic()
        status, job = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload=project_payload,
        )
        elapsed = time.monotonic() - started_at
        release_timer.join(timeout=2)
        assert status == 202
        assert elapsed < 0.3
        assert job["status"] == "running"

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status, created = request_json(
                base_url,
                f"/api/jobs/{job['job_id']}",
            )
            if created["status"] != "running":
                break
            time.sleep(0.01)

        assert status == 200
        assert created["status"] == "completed"
        assert created["workflow_id"] == workflow.workflow_id
        assert created["duration_ms"] == 12.5
        assert created["failed_stage"] is None
        assert created["landing_page"] == asdict(workflow.landing_page)
        assert received_commands == [
            (
                "客户项目：为「Alpha Studio」制作客户转化型网站包 | "
                "公司名称：Alpha Studio；目标客户：Malaysian SMEs；"
                "核心服务：AI websites；地区：Malaysia；语言：Chinese；"
                "行动号召：Book a consultation；"
                "联系方式：WhatsApp: +60123456789",
                stub_handlers,
            )
        ]

        status, error = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload={**project_payload, "company_name": " ", "cta": None},
        )
        assert status == 400
        assert error["error"] == (
            "Invalid project brief fields: company_name, cta"
        )

        status, history = request_json(base_url, "/api/workflows")
        assert status == 200
        assert history["runs"][0]["workflow_id"] == workflow.workflow_id

        status, detail = request_json(
            base_url,
            "/api/workflows/workflow-web-test",
        )
        assert status == 200
        assert detail["final_output"] == "Project output"
        assert detail["landing_page"] == asdict(workflow.landing_page)

        status, retry_job = request_json(
            base_url,
            "/api/workflows/workflow-failed/retry",
            method="POST",
        )
        assert status == 202
        assert retry_job["status"] == "running"

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status, retried = request_json(
                base_url,
                f"/api/jobs/{retry_job['job_id']}",
            )
            if retried["status"] != "running":
                break
            time.sleep(0.01)

        assert status == 200
        assert retried["status"] == "completed"
        assert received_commands[-1] == (
            "客户项目：Retry objective | Retry context",
            stub_handlers,
        )

        for workflow_id in ("workflow-web-test", "workflow-incomplete"):
            status, not_retryable = request_json(
                base_url,
                f"/api/workflows/{workflow_id}/retry",
                method="POST",
            )
            assert status == 409
            assert not_retryable["error"] == (
                "Only failed workflows can be retried."
            )

        status, missing_retry = request_json(
            base_url,
            "/api/workflows/missing/retry",
            method="POST",
        )
        assert status == 404
        assert missing_retry["error"] == "Workflow not found."

        status, headers, body = request_raw(
            base_url,
            "/api/workflows/workflow-web-test/download",
        )
        assert status == 200
        assert headers.get_content_type() == "application/zip"
        assert headers["Content-Disposition"] == (
            'attachment; filename="landing-page-workflow-web-test.zip"'
        )
        assert headers["Cache-Control"] == "no-store"
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            assert sorted(archive.namelist()) == [
                "index.html",
                "script.js",
                "styles.css",
            ]
            assert archive.read("index.html").decode("utf-8") == (
                "<main>Web</main>"
            )
            assert archive.read("styles.css").decode("utf-8") == (
                "main { color: black; }"
            )
            assert archive.read("script.js").decode("utf-8") == ""

        status, missing_download = request_json(
            base_url,
            "/api/workflows/missing/download",
        )
        assert status == 404
        assert missing_download["error"] == "Workflow not found."

        for workflow_id in (
            "workflow-incomplete",
            "workflow-invalid-package",
        ):
            status, unavailable = request_json(
                base_url,
                f"/api/workflows/{workflow_id}/download",
            )
            assert status == 409
            assert unavailable["error"] == "Landing page download unavailable."

        status, missing = request_json(
            base_url,
            "/api/workflows/missing",
        )
        assert status == 404
        assert missing["error"] == "Workflow not found."
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
