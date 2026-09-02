from client_project_workflow import (
    run_client_project_workflow,
)
from memory import contains_sensitive_memory
from workflow_history import (
    SENSITIVE_WORKFLOW_ERROR,
    save_workflow_run,
)


WORKFLOW_COMMAND_PREFIX = "工作流："
CLIENT_PROJECT_COMMAND_PREFIX = "客户项目："
WORKFLOW_COMMAND_USAGE = (
    "工作流格式：工作流：client_project | 目标 | 项目背景；"
    "或：客户项目：目标 | 项目背景"
)


def extract_workflow_request(user_input):
    if user_input.startswith(CLIENT_PROJECT_COMMAND_PREFIX):
        content = user_input[
            len(CLIENT_PROJECT_COMMAND_PREFIX):
        ]
        fields = [
            field.strip()
            for field in content.split("|", 1)
        ]

        if len(fields) != 2 or not all(fields):
            raise ValueError(WORKFLOW_COMMAND_USAGE)

        objective, context = fields
        return "client_project", objective, context

    if not user_input.startswith(WORKFLOW_COMMAND_PREFIX):
        return None

    content = user_input[
        len(WORKFLOW_COMMAND_PREFIX):
    ]
    fields = [
        field.strip()
        for field in content.split("|", 2)
    ]

    if len(fields) != 3 or not all(fields):
        raise ValueError(WORKFLOW_COMMAND_USAGE)

    workflow_type, objective, context = fields
    workflow_type = workflow_type.lower()

    if workflow_type != "client_project":
        raise ValueError(
            "Unsupported workflow type: "
            f"{workflow_type}"
        )

    return workflow_type, objective, context


def execute_workflow_request(
    user_input,
    handlers,
    run_workflow=run_client_project_workflow,
    save_run=save_workflow_run,
):
    request = extract_workflow_request(user_input)

    if request is None:
        return None

    _, objective, context = request

    if (
        contains_sensitive_memory(objective)
        or contains_sensitive_memory(context)
    ):
        raise ValueError(SENSITIVE_WORKFLOW_ERROR)

    result = run_workflow(
        objective,
        context,
        handlers,
    )
    save_run(objective, context, result)
    return result
