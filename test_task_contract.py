import importlib.util

module_spec = importlib.util.find_spec("task_contract")

assert module_spec is not None, "task_contract.py 尚未实现"

from task_contract import AgentResult, TaskBrief


task = TaskBrief(
    task_id="task-001",
    task_type="research",
    objective="研究客户市场",
    context="客户经营本地餐厅",
    assigned_agent="Search Agent",
)

assert task.task_id == "task-001"
assert task.assigned_agent == "Search Agent"

result = AgentResult(
    task_id="task-001",
    agent_name="Search Agent",
    status="completed",
    output="市场研究完成",
)

assert result.status == "completed"
assert result.output == "市场研究完成"
assert result.error is None

print("Task-contract tests passed.")