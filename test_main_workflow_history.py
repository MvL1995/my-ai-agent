import builtins
import io
import os
import runpy
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import agents
import memory
import workflow_history


project_directory = Path(__file__).resolve().parent
original_input = builtins.input
original_run_sync = agents.Runner.run_sync
original_memory_db_path = memory.DB_PATH
original_history_db_path = workflow_history.DB_PATH
original_get_workflow_run = workflow_history.get_workflow_run
requested_ids = []


def fake_get_workflow_run(workflow_id):
    requested_ids.append(workflow_id)
    if workflow_id == "missing":
        return None

    if workflow_id == "workflow-failed":
        return {
            "workflow_id": workflow_id,
            "workflow_type": "client_project",
            "objective": "失败项目",
            "context": "测试背景",
            "status": "failed",
            "steps": [
                {
                    "agent_name": "Search Agent",
                    "status": "failed",
                    "output": "",
                    "error": "search unavailable",
                }
            ],
            "final_output": "",
            "error": "Search Agent: search unavailable",
            "created_at": "2026-09-03 12:05:00",
        }

    return {
        "workflow_id": workflow_id,
        "workflow_type": "client_project",
        "objective": "客户官网上线",
        "context": "吉隆坡餐厅",
        "status": "completed",
        "steps": [
            {
                "agent_name": "Search Agent",
                "status": "completed",
                "output": "Research 完成",
                "error": None,
            }
        ],
        "final_output": "项目计划完成",
        "error": None,
        "created_at": "2026-09-03 12:00:00",
    }


def fake_run_sync(*args, **kwargs):
    return SimpleNamespace(
        interruptions=[],
        final_output="普通对话路径",
    )


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
    try:
        os.chdir(temp_dir)
        memory.DB_PATH = str(Path(temp_dir) / "memory.db")
        workflow_history.DB_PATH = str(Path(temp_dir) / "history.db")
        workflow_history.get_workflow_run = fake_get_workflow_run
        agents.Runner.run_sync = staticmethod(fake_run_sync)
        user_inputs = iter([
            "查看项目详情： workflow-123 ",
            "查看项目详情：missing",
            "查看项目详情：workflow-failed",
            "查看项目详情：   ",
            "exit",
        ])
        builtins.input = lambda prompt="": next(user_inputs)

        output = io.StringIO()
        with redirect_stdout(output):
            runpy.run_path(
                str(project_directory / "main.py"),
                run_name="day044_main_test",
            )

        text = output.getvalue()
        assert requested_ids == [
            "workflow-123", "missing", "workflow-failed"
        ]
        assert "目标：客户官网上线" in text
        assert "背景：吉隆坡餐厅" in text
        assert "Search Agent | completed：Research 完成" in text
        assert "最终结果：项目计划完成" in text
        assert "找不到项目记录：missing" in text
        assert "Search Agent | failed：search unavailable" in text
        assert "错误：Search Agent: search unavailable" in text
        assert "请输入工作流 ID。" in text
        assert "普通对话路径" not in text
    finally:
        builtins.input = original_input
        agents.Runner.run_sync = original_run_sync
        memory.DB_PATH = original_memory_db_path
        workflow_history.DB_PATH = original_history_db_path
        workflow_history.get_workflow_run = original_get_workflow_run

print("Main-workflow-history tests passed.")
