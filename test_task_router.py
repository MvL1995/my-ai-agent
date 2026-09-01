import importlib.util

module_spec = importlib.util.find_spec("task_router")

assert module_spec is not None, "task_router.py 尚未实现"

from task_contract import TaskBrief
from task_router import route_task


research_task = route_task(
    "  ReSeArCh  ",
    "  研究客户市场  ",
    "  客户经营本地餐厅  ",
)

assert isinstance(research_task, TaskBrief)
assert research_task.task_type == "research"
assert research_task.objective == "研究客户市场"
assert research_task.context == "客户经营本地餐厅"
assert research_task.assigned_agent == "Search Agent"

for unsupported_type in ("", " ", "unknown"):
    try:
        route_task(unsupported_type, "目标", "背景")
    except ValueError:
        pass
    else:
        raise AssertionError("未知或空白任务类型必须触发 ValueError")

print("Task-router tests passed.")
