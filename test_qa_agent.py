from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    qa_task = route_task(
        "  QA  ",
        "  审查餐厅短视频广告方案  ",
        "  验收要求：15 秒竖屏；必须包含 CTA  ",
    )
except ValueError as error:
    raise AssertionError(
        "qa 任务必须路由到 QA Agent"
    ) from error

assert isinstance(qa_task, TaskBrief)
assert qa_task.task_type == "qa"
assert qa_task.objective == "审查餐厅短视频广告方案"
assert qa_task.context == (
    "验收要求：15 秒竖屏；必须包含 CTA"
)
assert qa_task.assigned_agent == "QA Agent"

qa_agent = object()
received_requests = []


def run_qa(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "结论：需修改；问题：缺少 CTA；"
        "建议：补充明确行动号召。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        qa_agent=qa_agent,
        run_qa=run_qa,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 QA Agent"
    ) from error

completed = execute_task(qa_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "QA Agent"
assert completed.output == (
    "结论：需修改；问题：缺少 CTA；"
    "建议：补充明确行动号召。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is qa_agent
assert qa_task.objective in received_requests[0][1]
assert qa_task.context in received_requests[0][1]

print("QA-agent tests passed.")
