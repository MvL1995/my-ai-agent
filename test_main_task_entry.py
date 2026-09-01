import builtins
import os
import runpy
import tempfile
from pathlib import Path

import agent_registry
import agents
import memory
import task_entry
from search_cache import SearchCache
from task_contract import AgentResult


project_directory = Path(__file__).resolve().parent
original_input = builtins.input
original_db_path = memory.DB_PATH
original_build_handlers = agent_registry.build_agent_handlers
original_execute_request = task_entry.execute_task_request
original_run_sync = agents.Runner.run_sync
original_working_directory = Path.cwd()
captured = {}


def fake_build_handlers(
    search_agent,
    cache=None,
    strategy_agent=None,
    copywriting_agent=None,
    web_design_agent=None,
    coding_agent=None,
    video_ads_agent=None,
):
    handlers = {"Search Agent": object()}
    captured["cache"] = cache
    captured["handlers"] = handlers
    captured["strategy_agent"] = strategy_agent
    captured["copywriting_agent"] = copywriting_agent
    captured["web_design_agent"] = web_design_agent
    captured["coding_agent"] = coding_agent
    captured["video_ads_agent"] = video_ads_agent
    return handlers


def fake_execute_request(user_input, handlers):
    captured["user_input"] = user_input
    captured["received_handlers"] = handlers
    return AgentResult(
        task_id="task-test",
        agent_name="Search Agent",
        status="completed",
        output="任务入口接线成功",
    )


def forbidden_run_sync(*args, **kwargs):
    raise AssertionError(
        "显式任务命令不应进入普通 Main Agent 对话"
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
        task_entry.execute_task_request = (
            fake_execute_request
        )
        agents.Runner.run_sync = staticmethod(
            forbidden_run_sync
        )

        command = (
            "任务：research | 研究客户市场 | "
            "客户经营本地餐厅"
        )
        user_inputs = iter([command, "exit"])
        builtins.input = lambda prompt="": next(user_inputs)

        namespace = runpy.run_path(
            str(project_directory / "main.py"),
            run_name="day031_main_test",
        )

        assert isinstance(
            captured.get("cache"),
            SearchCache,
        )
        assert captured["cache"] is namespace["search_cache"]
        assert captured["strategy_agent"] is not None
        assert captured["strategy_agent"].name == (
            "Strategy Agent"
        )
        assert captured["copywriting_agent"] is not None
        assert captured["copywriting_agent"].name == (
            "Copywriting Agent"
        )
        assert captured["web_design_agent"] is not None
        assert captured["web_design_agent"].name == (
            "Web Design Agent"
        )
        assert captured["coding_agent"] is not None
        assert captured["coding_agent"].name == (
            "Coding Agent"
        )
        assert captured["video_ads_agent"] is not None
        assert captured["video_ads_agent"].name == (
            "Video Ads Agent"
        )
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
            original_execute_request
        )
        agents.Runner.run_sync = original_run_sync
        os.chdir(original_working_directory)

print("Main-task-entry tests passed.")
