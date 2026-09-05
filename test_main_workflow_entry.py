import builtins
import os
import runpy
import tempfile
from pathlib import Path

import agent_registry
import agents
import memory
import task_entry
import workflow_entry
from workflow_contract import WorkflowResult


project_directory = Path(__file__).resolve().parent
original_input = builtins.input
original_db_path = memory.DB_PATH
original_build_handlers = (
    agent_registry.build_agent_handlers
)
original_execute_task = task_entry.execute_task_request
original_execute_workflow = (
    workflow_entry.execute_workflow_request
)
original_run_sync = agents.Runner.run_sync
original_working_directory = Path.cwd()
captured = {}


def fake_build_handlers(*args, **kwargs):
    handlers = {"Search Agent": object()}
    captured["handlers"] = handlers
    return handlers


def fake_execute_workflow(user_input, handlers):
    captured["user_input"] = user_input
    captured["received_handlers"] = handlers
    return WorkflowResult(
        workflow_id="workflow-test",
        workflow_type="client_project",
        status="completed",
        steps=[],
        final_output="客户项目计划已生成",
    )


def forbidden_path(*args, **kwargs):
    raise AssertionError(
        "工作流命令不得进入单任务或普通对话路径"
    )


with tempfile.TemporaryDirectory(
    ignore_cleanup_errors=True
) as temp_dir:
    try:
        os.chdir(temp_dir)
        memory.DB_PATH = str(
            Path(temp_dir) / "test_memory.db"
        )
        agent_registry.build_agent_handlers = (
            fake_build_handlers
        )
        workflow_entry.execute_workflow_request = (
            fake_execute_workflow
        )
        task_entry.execute_task_request = forbidden_path
        agents.Runner.run_sync = staticmethod(
            forbidden_path
        )

        command = (
            "客户项目：启动客户项目 | 餐厅客户"
        )
        user_inputs = iter([command, "exit"])
        builtins.input = lambda prompt="": next(
            user_inputs
        )

        namespace = runpy.run_path(
            str(project_directory / "main.py"),
            run_name="day041_main_test",
        )
        namespace["run_cli"]()

        assert captured["user_input"] == command
        assert captured["received_handlers"] is (
            captured["handlers"]
        )
    finally:
        builtins.input = original_input
        memory.DB_PATH = original_db_path
        agent_registry.build_agent_handlers = (
            original_build_handlers
        )
        task_entry.execute_task_request = (
            original_execute_task
        )
        workflow_entry.execute_workflow_request = (
            original_execute_workflow
        )
        agents.Runner.run_sync = original_run_sync
        os.chdir(original_working_directory)

print("Main-workflow-entry tests passed.")
