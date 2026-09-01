from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    coding_task = route_task(
        "  CoDiNg  ",
        "  实现联系表单验证  ",
        "  Python 项目；空姓名必须被拒绝  ",
    )
except ValueError as error:
    raise AssertionError(
        "coding 任务必须路由到 Coding Agent"
    ) from error

assert isinstance(coding_task, TaskBrief)
assert coding_task.task_type == "coding"
assert coding_task.objective == "实现联系表单验证"
assert coding_task.context == (
    "Python 项目；空姓名必须被拒绝"
)
assert coding_task.assigned_agent == "Coding Agent"

coding_agent = object()
received_requests = []


def run_coding(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "修改：validation.py；测试：空姓名返回错误。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        coding_agent=coding_agent,
        run_coding=run_coding,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Coding Agent"
    ) from error

completed = execute_task(coding_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Coding Agent"
assert completed.output == (
    "修改：validation.py；测试：空姓名返回错误。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is coding_agent
assert coding_task.objective in received_requests[0][1]
assert coding_task.context in received_requests[0][1]

print("Coding-agent tests passed.")
