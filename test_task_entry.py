import importlib.util


module_spec = importlib.util.find_spec("task_entry")
assert module_spec is not None, "task_entry.py 尚未实现"

from task_entry import (
    TASK_COMMAND_USAGE,
    execute_task_request,
    extract_task_request,
)


assert extract_task_request("你好") is None
assert extract_task_request(
    "任务： research | 研究客户市场 | 客户经营本地餐厅 "
) == (
    "research",
    "研究客户市场",
    "客户经营本地餐厅",
)

received_tasks = []


def research_handler(task):
    received_tasks.append(task)
    return "研究任务已完成"


result = execute_task_request(
    "任务：research | 研究客户市场 | 客户经营本地餐厅",
    {"Search Agent": research_handler},
)

assert result.status == "completed"
assert result.output == "研究任务已完成"
assert len(received_tasks) == 1
assert received_tasks[0].objective == "研究客户市场"
assert received_tasks[0].context == "客户经营本地餐厅"

for invalid_input in (
    "任务：",
    "任务：research | 研究客户市场",
    "任务：research | | 客户经营本地餐厅",
):
    try:
        extract_task_request(invalid_input)
    except ValueError as error:
        assert str(error) == TASK_COMMAND_USAGE
    else:
        raise AssertionError("无效任务命令必须触发 ValueError")

print("Task-entry tests passed.")
