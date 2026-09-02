from client_project_workflow import (
    run_client_project_workflow,
)


WORKFLOW_COMMAND_PREFIX = "工作流："
WORKFLOW_COMMAND_USAGE = (
    "工作流格式：工作流：client_project | 目标 | 项目背景"
)


def extract_workflow_request(user_input):
    if not user_input.startswith(
        WORKFLOW_COMMAND_PREFIX
    ):
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
):
    request = extract_workflow_request(user_input)

    if request is None:
        return None

    _, objective, context = request
    return run_workflow(objective, context, handlers)
