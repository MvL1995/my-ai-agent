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
        self.decision = None
        self.retry_button = None
        self.lineage = None
        self.attempts = None
        self.retry_metrics = None
        self.override_breakdown = None

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
        if tag == "p" and element_id == "workflow-decision":
            self.decision = attributes
        if tag == "button" and element_id == "retry-button":
            self.retry_button = attributes
        if tag == "p" and element_id == "workflow-lineage":
            self.lineage = attributes
        if tag == "div" and element_id == "workflow-attempts":
            self.attempts = attributes
        if tag == "div" and element_id == "retry-metrics":
            self.retry_metrics = attributes
        if tag == "div" and element_id == "override-breakdown":
            self.override_breakdown = attributes


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
    "failure_type": None,
    "retry_recommended": False,
    "recommended_action": None,
    "policy_adjusted": False,
    "attempts": [
        {
            "workflow_id": "workflow-web-test",
            "status": "completed",
            "attempt_number": 1,
            "duration_ms": 12.5,
            "failed_stage": None,
        },
    ],
    "created_at": "2026-09-05 12:00:00",
}
failed_workflow_record = {
    **workflow_record,
    "workflow_id": "workflow-failed",
    "status": "failed",
    "objective": "Retry objective",
    "context": "Retry context",
    "landing_page": None,
    "error": "Search Agent: search unavailable",
    "failed_stage": "Search Agent",
    "failure_type": "transient",
    "retry_recommended": True,
    "recommended_action": "建议重跑：临时故障通常可恢复。",
    "retry_of": "workflow-root",
    "attempt_number": 2,
    "attempts": [
        {
            "workflow_id": "workflow-root",
            "status": "failed",
            "attempt_number": 1,
            "duration_ms": 20,
            "failed_stage": "Search Agent",
        },
        {
            "workflow_id": "workflow-failed",
            "status": "failed",
            "attempt_number": 2,
            "duration_ms": 12.5,
            "failed_stage": "Search Agent",
        },
    ],
}
validation_workflow_record = {
    **failed_workflow_record,
    "workflow_id": "workflow-invalid-output",
    "error": "Coding Agent: Coding Agent 必须返回有效 JSON。",
    "failed_stage": "Coding Agent",
    "failure_type": "validation",
    "retry_recommended": False,
    "recommended_action": "先修正输出格式，再执行。",
    "retry_of": None,
    "attempt_number": 1,
    "attempts": [
        {
            "workflow_id": "workflow-invalid-output",
            "status": "failed",
            "attempt_number": 1,
            "duration_ms": 12.5,
            "failed_stage": "Coding Agent",
        },
    ],
}
low_hit_workflow_record = {
    **failed_workflow_record,
    "workflow_id": "workflow-low-hit",
    "objective": "Override objective",
    "context": "Override context",
    "error": "Search Agent: Provider rejected request",
    "failed_stage": "Search Agent",
    "failure_type": "external_dependency",
    "retry_recommended": False,
    "policy_adjusted": True,
    "historical_hit_rate": 33.3,
    "historical_sample_size": 3,
    "historical_override_success_rate": 0.0,
    "historical_override_sample_size": 3,
    "override_risk_level": "high",
    "override_risk_warning": (
        "高风险：该组风险提示后仍有 66.7% 继续人工覆盖（2/3），"
        "覆盖后恢复率仅 0.0%（0/2）；仍可由人工决定是否继续。"
    ),
    "recommended_action": (
        "历史重跑命中率仅 33.3%（1/3），不建议继续重跑；先检查失败详情。"
    ),
    "retry_of": None,
    "attempt_number": 1,
    "attempts": [
        {
            "workflow_id": "workflow-low-hit",
            "status": "failed",
            "attempt_number": 1,
            "duration_ms": 12.5,
            "failed_stage": "Search Agent",
        },
    ],
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


def fake_execute(
    command, handlers, retry_of=None, attempt_number=1,
    override_source=None, override_reason=None,
):
    received_commands.append(
        (command, handlers, retry_of, attempt_number, override_source, override_reason)
    )
    workflow.retry_of = retry_of
    workflow.attempt_number = attempt_number
    workflow.override_source = override_source
    workflow.override_reason = override_reason
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
    if workflow_id == validation_workflow_record["workflow_id"]:
        return validation_workflow_record
    if workflow_id == low_hit_workflow_record["workflow_id"]:
        return low_hit_workflow_record
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

def fake_next_attempt_number(root_workflow_id):
    if root_workflow_id == "workflow-root":
        return 3
    if root_workflow_id == "workflow-low-hit":
        return 2
    assert root_workflow_id == "workflow-invalid-output"
    return 2


def fake_read_retry_metrics():
    return {
        "retry_chains": 2,
        "recovered_chains": 1,
        "recovery_rate": 50.0,
        "duration_samples": 2,
        "average_duration_change_ms": -125.5,
        "top_failed_stage": "Coding Agent",
        "retry_recommendations": 4,
        "accepted_recommendations": 3,
        "recommendation_adoption_rate": 75.0,
        "recommendation_hits": 2,
        "decision_hit_rate": 66.7,
        "manual_overrides": 4,
        "successful_overrides": 1,
        "override_success_rate": 25.0,
        "risk_warnings": 4,
        "risk_warning_overrides": 2,
        "risk_warning_adoption_rate": 50.0,
        "risk_warning_recoveries": 1,
        "risk_warning_recovery_rate": 50.0,
        "risk_warning_breakdown": [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "warnings": 3,
                "overrides": 2,
                "adoption_rate": 66.7,
                "recoveries": 1,
                "recovery_rate": 50.0,
                "sample_sufficient": True,
                "risk_level": "medium",
                "risk_events": 5,
                "level_changes": 1,
                "change_rate": 20.0,
                "jitters": 0,
                "jitter_rate": 0.0,
                "hysteresis": 10.0,
                "hysteresis_calibrated": False,
            },
            {
                "failure_type": "external_dependency",
                "failed_stage": "Search Agent",
                "warnings": 1,
                "overrides": 0,
                "adoption_rate": 0.0,
                "recoveries": 0,
                "recovery_rate": None,
                "sample_sufficient": False,
                "risk_level": "medium",
                "risk_events": 1,
                "level_changes": 0,
                "change_rate": 0.0,
                "jitters": 0,
                "jitter_rate": None,
                "hysteresis": 10.0,
                "hysteresis_calibrated": False,
            },
        ],
        "risk_level_transitions": [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "from_level": "high",
                "to_level": "medium",
                "workflow_id": "workflow-transient-risk-downgraded",
                "warnings": 8,
                "overrides": 3,
                "adoption_rate": 37.5,
                "recoveries": 1,
                "recovery_rate": 33.3,
            },
        ],
        "risk_level_events": 6,
        "risk_level_changes": 1,
        "risk_level_change_rate": 16.7,
        "risk_level_jitters": 0,
        "risk_level_jitter_rate": 0.0,
        "calibrated_hysteresis_groups": 0,
        "override_breakdown": [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "overrides": 3,
                "successful": 0,
                "success_rate": 0.0,
                "sample_sufficient": True,
            },
            {
                "failure_type": "external_dependency",
                "failed_stage": "Search Agent",
                "overrides": 1,
                "successful": 1,
                "success_rate": 100.0,
                "sample_sufficient": False,
            },
        ],
        "minimum_decision_samples": 3,
        "decision_breakdown": [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "recommendations": 3,
                "accepted": 3,
                "hits": 2,
                "hit_rate": 66.7,
                "sample_sufficient": True,
            },
            {
                "failure_type": "external_dependency",
                "failed_stage": "Search Agent",
                "recommendations": 1,
                "accepted": 0,
                "hits": 0,
                "hit_rate": None,
                "sample_sufficient": False,
            },
        ],
    }


handler = build_request_handler(
    stub_handlers,
    execute_workflow=fake_execute,
    list_runs=fake_list_runs,
    read_run=fake_read_run,
    next_attempt_number=fake_next_attempt_number,
    read_retry_metrics=fake_read_retry_metrics,
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
        assert "人工覆盖并重跑" in page
        assert "高风险人工覆盖并重跑" in page
        assert "这是高风险操作" in page
        assert '[data-risk="high"]' in page
        assert "override_reason" in page
        assert "人工覆盖成功率" in page
        assert "可信低效覆盖" in page
        assert (
            '+ ` · 高频失败：${metrics.top_failed_stage || "暂无"}`\n'
            '          + ` · 风险提示后覆盖率：${riskAdoption}`\n'
            '          + ` · 提示后覆盖恢复率：${riskRecovery}`;'
        ) in page
        assert "可信提示效果" in page
        assert "最近等级变更" in page
        assert "等级抖动率" in page
        assert "滞回区间" in page
        for field_name in project_payload:
            assert f'name="{field_name}"' in page
        assert 'id="history-list"' in page
        preview = PreviewContractParser()
        assert "仍要人工覆盖吗？" in page
        preview.feed(page)
        assert preview.empty_state is not None
        assert preview.frame is not None
        assert preview.frame.get("sandbox") == "allow-scripts"
        assert "hidden" in preview.frame
        assert preview.download_button is not None
        assert preview.decision is not None
        assert preview.decision.get("role") == "status"
        assert preview.diagnostics is not None
        assert "hidden" in preview.download_button

        assert preview.retry_button is not None
        assert preview.lineage is not None
        assert preview.attempts is not None
        assert preview.retry_metrics is not None
        assert preview.retry_metrics.get("aria-label") == "重跑成效"
        assert preview.override_breakdown is not None
        assert preview.override_breakdown.get("aria-label") == "人工覆盖细分"
        assert preview.override_breakdown.get("role") == "status"
        assert preview.override_breakdown.get("aria-live") == "polite"
        assert preview.attempts.get("aria-label") == "重跑链对比"
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
                None,
                1,
                None,
                None,
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
        assert history["retry_metrics"] == {
            "retry_chains": 2,
            "recovered_chains": 1,
            "recovery_rate": 50.0,
            "duration_samples": 2,
            "average_duration_change_ms": -125.5,
            "top_failed_stage": "Coding Agent",
            "retry_recommendations": 4,
            "accepted_recommendations": 3,
            "recommendation_adoption_rate": 75.0,
            "recommendation_hits": 2,
            "decision_hit_rate": 66.7,
            "minimum_decision_samples": 3,
            "manual_overrides": 4,
            "successful_overrides": 1,
            "override_success_rate": 25.0,
            "risk_warnings": 4,
            "risk_warning_overrides": 2,
            "risk_warning_adoption_rate": 50.0,
            "risk_warning_recoveries": 1,
            "risk_warning_recovery_rate": 50.0,
            "risk_warning_breakdown": [
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "warnings": 3,
                    "overrides": 2,
                    "adoption_rate": 66.7,
                    "recoveries": 1,
                    "recovery_rate": 50.0,
                    "sample_sufficient": True,
                    "risk_level": "medium",
                    "risk_events": 5,
                    "level_changes": 1,
                    "change_rate": 20.0,
                    "jitters": 0,
                    "jitter_rate": 0.0,
                    "hysteresis": 10.0,
                    "hysteresis_calibrated": False,
                },
                {
                    "failure_type": "external_dependency",
                    "failed_stage": "Search Agent",
                    "warnings": 1,
                    "overrides": 0,
                    "adoption_rate": 0.0,
                    "recoveries": 0,
                    "recovery_rate": None,
                    "sample_sufficient": False,
                    "risk_level": "medium",
                    "risk_events": 1,
                    "level_changes": 0,
                    "change_rate": 0.0,
                    "jitters": 0,
                    "jitter_rate": None,
                    "hysteresis": 10.0,
                    "hysteresis_calibrated": False,
                },
            ],
            "risk_level_transitions": [
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "from_level": "high",
                    "to_level": "medium",
                    "workflow_id": "workflow-transient-risk-downgraded",
                    "warnings": 8,
                    "overrides": 3,
                    "adoption_rate": 37.5,
                    "recoveries": 1,
                    "recovery_rate": 33.3,
                },
            ],
            "risk_level_events": 6,
            "risk_level_changes": 1,
            "risk_level_change_rate": 16.7,
            "risk_level_jitters": 0,
            "risk_level_jitter_rate": 0.0,
            "calibrated_hysteresis_groups": 0,
            "override_breakdown": [
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "overrides": 3,
                    "successful": 0,
                    "success_rate": 0.0,
                    "sample_sufficient": True,
                },
                {
                    "failure_type": "external_dependency",
                    "failed_stage": "Search Agent",
                    "overrides": 1,
                    "successful": 1,
                    "success_rate": 100.0,
                    "sample_sufficient": False,
                },
            ],
            "decision_breakdown": [
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "recommendations": 3,
                    "accepted": 3,
                    "hits": 2,
                    "hit_rate": 66.7,
                    "sample_sufficient": True,
                },
                {
                    "failure_type": "external_dependency",
                    "failed_stage": "Search Agent",
                    "recommendations": 1,
                    "accepted": 0,
                    "hits": 0,
                    "hit_rate": None,
                    "sample_sufficient": False,
                },
            ],
        }

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
        assert retried["retry_of"] == "workflow-root"
        assert retried["attempt_number"] == 3
        assert received_commands[-1] == (
            "客户项目：Retry objective | Retry context",
            stub_handlers,
            "workflow-root",
            3,
            None,
            None,
        )

        command_count = len(received_commands)
        status, rejected_retry = request_json(
            base_url,
            "/api/workflows/workflow-invalid-output/retry",
            method="POST",
            payload={"override_reason": "强制尝试"},
        )
        assert status == 409
        assert rejected_retry["error"] == "先修正输出格式，再执行。"
        assert len(received_commands) == command_count
        invalid_overrides = (
            (None, "override_reason is required."),
            ({"override_reason": " "}, "override_reason is required."),
            (
                {"override_reason": "x" * 201},
                "override_reason must be at most 200 characters.",
            ),
            (
                {"override_reason": "API Key: secret"},
                "拒绝工作流：检测到密码、API Key、Token 或密钥。",
            ),
        )
        for payload, expected_error in invalid_overrides:
            status, rejected_override = request_json(
                base_url,
                "/api/workflows/workflow-low-hit/retry",
                method="POST",
                payload=payload,
            )
            assert status == 400
            assert rejected_override["error"] == expected_error
        assert len(received_commands) == command_count

        override_reason = "供应商状态已人工确认恢复"
        status, override_job = request_json(
            base_url,
            "/api/workflows/workflow-low-hit/retry",
            method="POST",
            payload={"override_reason": override_reason},
        )
        assert status == 202
        assert override_job["status"] == "running"

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status, overridden = request_json(
                base_url,
                f"/api/jobs/{override_job['job_id']}",
            )
            if overridden["status"] != "running":
                break
            time.sleep(0.01)

        assert status == 200
        assert overridden["status"] == "completed"
        assert overridden["override_source"] == "workflow-low-hit"
        assert overridden["override_reason"] == override_reason
        assert received_commands[-1] == (
            "客户项目：Override objective | Override context",
            stub_handlers,
            "workflow-low-hit",
            2,
            "workflow-low-hit",
            override_reason,
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
