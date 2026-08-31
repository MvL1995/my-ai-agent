from task_pipeline import run_task_pipeline


TASK_COMMAND_PREFIX = "任务："
TASK_COMMAND_USAGE = (
    "任务格式：任务：task_type | 目标 | 背景"
)


def extract_task_request(user_input):
    if not user_input.startswith(TASK_COMMAND_PREFIX):
        return None

    content = user_input[len(TASK_COMMAND_PREFIX):]
    fields = [
        field.strip()
        for field in content.split("|", 2)
    ]

    if len(fields) != 3 or not all(fields):
        raise ValueError(TASK_COMMAND_USAGE)

    return tuple(fields)


def execute_task_request(user_input, handlers):
    request = extract_task_request(user_input)

    if request is None:
        return None

    return run_task_pipeline(*request, handlers)
