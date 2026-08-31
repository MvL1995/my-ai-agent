import importlib.util
import os
import tempfile

import memory


module_spec = importlib.util.find_spec("agent_registry")
assert module_spec is not None, "agent_registry.py 尚未实现"

from agent_registry import build_agent_handlers
from task_executor import execute_task
from task_router import route_task


original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(
        temp_dir,
        "test_memory.db",
    )

    try:
        memory.init_memory_db()
        search_agent = object()
        requests = []

        def successful_search(received_agent, request):
            requests.append((received_agent, request))
            return "找到市场机会：https://example.com/research"

        handlers = build_agent_handlers(
            search_agent,
            run_search=successful_search,
        )
        task = route_task(
            "research",
            "研究吉隆坡餐饮市场",
            "客户准备推出新的午餐套餐",
        )
        completed = execute_task(task, handlers)

        assert set(handlers) == {"Search Agent"}
        assert completed.status == "completed"
        assert completed.output == (
            "找到市场机会：https://example.com/research"
        )
        assert completed.error is None
        assert len(requests) == 1
        assert requests[0][0] is search_agent
        assert task.objective in requests[0][1]
        assert task.context in requests[0][1]

        def invalid_search(received_agent, request):
            return "没有来源链接"

        failed = execute_task(
            task,
            build_agent_handlers(
                search_agent,
                run_search=invalid_search,
            ),
        )

        assert failed.status == "failed"
        assert failed.output == ""
        assert failed.error == (
            "搜索结果缺少有效来源，请稍后重试。"
        )
    finally:
        memory.DB_PATH = original_db_path

print("Agent-registry tests passed.")
