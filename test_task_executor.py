import importlib.util


module_spec = importlib.util.find_spec("task_executor")
assert module_spec is not None, "task_executor.py 尚未实现"

from task_contract import AgentResult
from task_executor import execute_task
from task_factory import create_task


task = create_task(
    "research",
    "研究客户市场",
    "客户经营本地餐厅",
    "Search Agent",
)
received_tasks = []


def successful_handler(received_task):
    received_tasks.append(received_task)
    return "找到三个市场机会"


completed = execute_task(
    task,
    {"Search Agent": successful_handler},
)

assert isinstance(completed, AgentResult)
assert received_tasks == [task]
assert completed.task_id == task.task_id
assert completed.agent_name == "Search Agent"
assert completed.status == "completed"
assert completed.output == "找到三个市场机会"
assert completed.error is None
assert completed.duration_ms > 0


def failing_handler(received_task):
    raise RuntimeError("搜索暂时不可用")


failed = execute_task(
    task,
    {"Search Agent": failing_handler},
)

assert isinstance(failed, AgentResult)
assert failed.task_id == task.task_id
assert failed.agent_name == "Search Agent"
assert failed.status == "failed"
assert failed.output == ""
assert failed.error == "搜索暂时不可用"
assert failed.duration_ms > 0

try:
    execute_task(task, {})
except ValueError:
    pass
else:
    raise AssertionError("未注册的 Agent 必须触发 ValueError")

print("Task-executor tests passed.")
