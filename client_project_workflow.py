from uuid import uuid4

from landing_page_package import parse_landing_page_package
from task_executor import execute_task
from task_router import route_task
from workflow_contract import WorkflowResult


PIPELINE = (
    ("research", "Research", ()),
    ("strategy", "Strategy", ("Research",)),
    (
        "copywriting",
        "Copywriting",
        ("Research", "Strategy"),
    ),
    (
        "web_design",
        "Web Design",
        ("Strategy", "Copywriting"),
    ),
    (
        "coding",
        "Coding",
        ("Copywriting", "Web Design"),
    ),
    (
        "qa",
        "QA",
        ("Copywriting", "Web Design", "Coding"),
    ),
    (
        "client_management",
        "Client Project Manager",
        (
            "Research",
            "Strategy",
            "Copywriting",
            "Web Design",
            "Coding",
            "QA",
        ),
    ),
)


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


def _build_step_context(context, outputs, dependencies):
    if not dependencies:
        return context

    blocks = [f"原始项目背景：\n{context}"]
    blocks.extend(
        f"{name} 输出：\n{outputs[name]}"
        for name in dependencies
    )
    return "\n\n".join(blocks)


def run_client_project_workflow(
    objective,
    context,
    handlers,
):
    workflow_id = f"workflow-{uuid4().hex}"
    steps = []
    outputs = {}
    landing_page = None

    for task_type, output_name, dependencies in PIPELINE:
        step_objective = objective
        if task_type == "coding":
            step_objective = (
                "生成可交付 Landing Page 网站包。\n"
                f"原始项目目标：{objective}"
            )

        step = _run_step(
            task_type,
            step_objective,
            _build_step_context(
                context,
                outputs,
                dependencies,
            ),
            handlers,
        )
        steps.append(step)

        if step.status == "failed":
            return _failed_workflow(workflow_id, steps)

        if output_name == "Coding":
            try:
                landing_page = parse_landing_page_package(step.output)
            except ValueError as error:
                step.status = "failed"
                step.error = str(error)
                return _failed_workflow(workflow_id, steps)

        outputs[output_name] = step.output

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=steps,
        final_output=steps[-1].output,
        landing_page=landing_page,
    )
