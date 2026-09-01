from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    copywriting_task = route_task(
        "  CoPyWrItInG  ",
        "  为午餐套餐写广告  ",
        "  吉隆坡上班族，套餐 RM15  ",
    )
except ValueError as error:
    raise AssertionError(
        "copywriting 任务必须路由到 Copywriting Agent"
    ) from error

assert isinstance(copywriting_task, TaskBrief)
assert copywriting_task.task_type == "copywriting"
assert copywriting_task.objective == "为午餐套餐写广告"
assert copywriting_task.context == "吉隆坡上班族，套餐 RM15"
assert copywriting_task.assigned_agent == "Copywriting Agent"

copywriting_agent = object()
received_requests = []


def run_copywriting(received_agent, request):
    received_requests.append((received_agent, request))
    return "标题：午餐省时也省钱\n正文：RM15 套餐\nCTA：立即到店"


try:
    handlers = build_agent_handlers(
        object(),
        copywriting_agent=copywriting_agent,
        run_copywriting=run_copywriting,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Copywriting Agent"
    ) from error

completed = execute_task(copywriting_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Copywriting Agent"
assert completed.output == (
    "标题：午餐省时也省钱\n正文：RM15 套餐\nCTA：立即到店"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is copywriting_agent
assert copywriting_task.objective in received_requests[0][1]
assert copywriting_task.context in received_requests[0][1]

print("Copywriting-agent tests passed.")
