import json
import os
import subprocess
import sys
import tempfile
import threading
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

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if tag == "p" and element_id == "preview-empty":
            self.empty_state = attributes
        if tag == "iframe" and element_id == "preview-frame":
            self.frame = attributes


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
received_commands = []
stub_handlers = {"Search Agent": object()}


def fake_execute(command, handlers):
    received_commands.append((command, handlers))
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
        assert 'id="history-list"' in page
        preview = PreviewContractParser()
        preview.feed(page)
        assert preview.empty_state is not None
        assert preview.frame is not None
        assert preview.frame.get("sandbox") == "allow-scripts"
        assert "hidden" in preview.frame

        with urlopen(base_url + "/tokens.css", timeout=5) as response:
            tokens = response.read().decode("utf-8")
        assert "--color-accent" in tokens

        status, created = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload={
                "objective": "Build a restaurant landing page",
                "context": "Kuala Lumpur restaurant",
            },
        )
        assert status == 200
        assert created["workflow_id"] == workflow.workflow_id
        assert created["landing_page"] == asdict(workflow.landing_page)
        assert received_commands == [
            (
                "客户项目：Build a restaurant landing page | "
                "Kuala Lumpur restaurant",
                stub_handlers,
            )
        ]

        status, error = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload={"objective": " ", "context": "context"},
        )
        assert status == 400
        assert error["error"] == "objective cannot be empty."

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
