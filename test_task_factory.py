import importlib.util

module_spec = importlib.util.find_spec("task_factory")

assert module_spec is not None, "task_factory.py 尚未实现"

from task_contract import TaskBrief
from task_factory import create_task


first_task = create_task(
    "research",
    "  研究客户市场  ",
    "  客户经营本地餐厅  ",
    "  Search Agent  ",
)

second_task = create_task(
    "research",
    "研究竞争对手",
    "客户经营本地餐厅",
    "Search Agent",
)

assert isinstance(first_task, TaskBrief)
assert first_task.task_id.startswith("task-")
assert first_task.task_id != second_task.task_id
assert first_task.objective == "研究客户市场"
assert first_task.context == "客户经营本地餐厅"
assert first_task.assigned_agent == "Search Agent"

invalid_inputs = (
    ("", "目标", "背景", "Search Agent"),
    ("research", " ", "背景", "Search Agent"),
    ("research", "目标", "", "Search Agent"),
    ("research", "目标", "背景", " "),
)

for arguments in invalid_inputs:
    try:
        create_task(*arguments)
    except ValueError:
        pass
    else:
        raise AssertionError("空白必填字段必须触发 ValueError")

print("Task-factory tests passed.")