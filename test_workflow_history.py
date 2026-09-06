import importlib.util
import json
import os
import sqlite3
import tempfile
from contextlib import closing

module_spec = importlib.util.find_spec("workflow_history")
assert module_spec is not None, "workflow_history.py 尚未实现"

import workflow_history
from task_contract import AgentResult
from workflow_contract import WorkflowResult


original_db_path = workflow_history.DB_PATH
landing_page_files = {
    "index.html": "<main>Stored</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}

with tempfile.TemporaryDirectory() as temp_dir:
    workflow_history.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        with closing(sqlite3.connect(workflow_history.DB_PATH)) as conn:
            conn.execute(
                """
                CREATE TABLE workflow_runs (
                    workflow_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    context TEXT NOT NULL,
                    status TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    final_output TEXT NOT NULL,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        workflow_history.init_workflow_history_db()
        with closing(sqlite3.connect(workflow_history.DB_PATH)) as conn:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(workflow_runs)")
            }
        assert {"retry_of", "attempt_number"} <= columns

        completed = WorkflowResult(
            workflow_id="workflow-completed",
            workflow_type="client_project",
            status="completed",
            steps=[
                AgentResult("task-research", "Search Agent", "completed", "Research 完成"),
                AgentResult("task-strategy", "Strategy Agent", "completed", "Strategy 完成"),
                AgentResult(
                    "task-coding",
                    "Coding Agent",
                    "completed",
                    json.dumps(landing_page_files),
                ),
                AgentResult("task-project", "Client Project Manager Agent", "completed", "项目计划完成"),
            ],
            final_output="项目计划完成",
        )
        completed.steps[0].duration_ms = 12.5

        workflow_history.save_workflow_run("启动餐厅项目", "吉隆坡本地餐厅", completed)

        stored = workflow_history.get_workflow_run("workflow-completed")
        assert stored["objective"] == "启动餐厅项目"
        assert stored["context"] == "吉隆坡本地餐厅"
        assert stored["status"] == "completed"
        assert stored["final_output"] == "项目计划完成"
        assert [step["agent_name"] for step in stored["steps"]] == [
            "Search Agent", "Strategy Agent", "Coding Agent",
            "Client Project Manager Agent",
        ]
        assert stored["landing_page"] == {
            "files": landing_page_files,
        }
        assert stored["duration_ms"] == 12.5
        assert stored["failed_stage"] is None
        assert stored["retry_of"] is None
        assert stored["attempt_number"] == 1

        failed = WorkflowResult(
            workflow_id="workflow-failed",
            workflow_type="client_project",
            status="failed",
            steps=[AgentResult("task-research-failed", "Search Agent", "failed", "", "search unavailable")],
            final_output="",
            error="Search Agent: search unavailable",
        )
        failed.steps[0].duration_ms = 8.5
        workflow_history.save_workflow_run("失败项目", "测试背景", failed)

        stored_failed = workflow_history.get_workflow_run("workflow-failed")
        assert stored_failed["status"] == "failed"
        assert len(stored_failed["steps"]) == 1
        assert stored_failed["error"] == "Search Agent: search unavailable"
        assert stored_failed["landing_page"] is None

        assert stored_failed["duration_ms"] == 8.5
        assert stored_failed["failed_stage"] == "Search Agent"
        recent = workflow_history.get_workflow_history(limit=1)
        assert len(recent) == 1
        assert recent[0]["workflow_id"] == "workflow-failed"
        assert recent[0]["retry_of"] is None
        assert recent[0]["attempt_number"] == 1
        assert workflow_history.get_workflow_run("missing") is None

        assert workflow_history.get_next_attempt_number("workflow-failed") == 2
        retry = WorkflowResult(
            workflow_id="workflow-retry-2",
            workflow_type="client_project",
            status="completed",
            steps=[],
            final_output="重跑完成",
            retry_of="workflow-failed",
            attempt_number=2,
        )
        workflow_history.save_workflow_run("失败项目", "测试背景", retry)

        stored_retry = workflow_history.get_workflow_run("workflow-retry-2")
        assert stored_retry["retry_of"] == "workflow-failed"
        assert stored_retry["attempt_number"] == 2
        assert workflow_history.get_next_attempt_number("workflow-failed") == 3

        try:
            workflow_history.get_workflow_history(limit=0)
        except ValueError:
            pass
        else:
            raise AssertionError("非正数 limit 必须被拒绝")

        try:
            workflow_history.get_workflow_run(" ")
        except ValueError:
            pass
        else:
            raise AssertionError("空 workflow_id 必须被拒绝")

        try:
            workflow_history.save_workflow_run("重复项目", "重复背景", completed)
        except RuntimeError:
            pass
        else:
            raise AssertionError("重复 workflow_id 必须失败")

        sensitive = WorkflowResult(
            workflow_id="workflow-sensitive",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult("task-sensitive", "Search Agent", "completed", "API Key: secret")],
            final_output="敏感输出",
        )
        try:
            workflow_history.save_workflow_run("敏感项目", "测试背景", sensitive)
        except ValueError as error:
            assert str(error) == workflow_history.SENSITIVE_WORKFLOW_ERROR
        else:
            raise AssertionError("敏感输出不得保存")

        assert workflow_history.get_workflow_run("workflow-sensitive") is None

        sensitive_metadata = WorkflowResult(
            workflow_id="workflow-sensitive-metadata",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult(
                "task-sensitive-metadata",
                "API Key owner",
                "completed",
                "safe output",
            )],
            final_output="safe output",
        )
        try:
            workflow_history.save_workflow_run(
                "普通项目", "测试背景", sensitive_metadata
            )
        except ValueError as error:
            assert str(error) == workflow_history.SENSITIVE_WORKFLOW_ERROR
        else:
            raise AssertionError("敏感元数据不得保存")

        assert workflow_history.get_workflow_run(
            "workflow-sensitive-metadata"
        ) is None
    finally:
        workflow_history.DB_PATH = original_db_path

print("Workflow-history tests passed.")
