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


def _failed_workflow(workflow_id, steps):
    failed_step = steps[-1]
    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="failed",
        steps=steps,
        final_output="",
        error=(
            f"{failed_step.agent_name}: "
            f"{failed_step.error}"
        ),
    )


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
    steps = [research]

    if research.status == "failed":
        return _failed_workflow(workflow_id, steps)

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
    steps.append(strategy)

    if strategy.status == "failed":
        return _failed_workflow(workflow_id, steps)

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
    steps.append(project)

    if project.status == "failed":
        return _failed_workflow(workflow_id, steps)

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=steps,
        final_output=project.output,
    )
