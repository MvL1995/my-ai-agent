import importlib.util


contract_spec = importlib.util.find_spec("workflow_contract")
workflow_spec = importlib.util.find_spec(
    "client_project_workflow"
)

assert contract_spec is not None, (
    "workflow_contract.py 尚未实现"
)
assert workflow_spec is not None, (
    "client_project_workflow.py 尚未实现"
)

from client_project_workflow import (
    run_client_project_workflow,
)
from workflow_contract import WorkflowResult


received_tasks = []


def handler(output):
    def run(task):
        received_tasks.append(task)
        return output

    return run


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Client Project Manager Agent": handler(
            "项目计划完成"
        ),
    },
)

assert isinstance(result, WorkflowResult)
assert result.workflow_id.startswith("workflow-")
assert result.workflow_type == "client_project"
assert result.status == "completed"
assert result.final_output == "项目计划完成"
assert result.error is None
assert [step.agent_name for step in result.steps] == [
    "Search Agent",
    "Strategy Agent",
    "Client Project Manager Agent",
]

assert received_tasks[0].task_type == "research"
assert received_tasks[0].context == (
    "客户经营吉隆坡本地餐厅"
)

assert received_tasks[1].task_type == "strategy"
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[1].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[1].context
)

assert received_tasks[2].task_type == (
    "client_management"
)
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[2].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[2].context
)
assert "Strategy 输出：\nStrategy 完成" in (
    received_tasks[2].context
)

print("Client-project-workflow tests passed.")
