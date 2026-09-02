from uuid import uuid4

from task_executor import execute_task
from task_router import route_task
from workflow_contract import WorkflowResult


def _run_step(
    task_type,
    objective,
    context,
    handlers,
):
    task = route_task(
        task_type,
        objective,
        context,
    )
    return execute_task(task, handlers)


def run_client_project_workflow(
    objective,
    context,
    handlers,
):
    workflow_id = f"workflow-{uuid4().hex}"

    research = _run_step(
        "research",
        objective,
        context,
        handlers,
    )
    strategy_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}"
    )
    strategy = _run_step(
        "strategy",
        objective,
        strategy_context,
        handlers,
    )
    project_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}\n\n"
        f"Strategy 输出：\n{strategy.output}"
    )
    project = _run_step(
        "client_management",
        objective,
        project_context,
        handlers,
    )

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=[research, strategy, project],
        final_output=project.output,
    )
