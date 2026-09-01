from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    analytics_task = route_task(
        "  AnAlYtIcS  ",
        "  分析广告表现  ",
        "  展示 10000；点击 300；转化 12；目标：增加转化  ",
    )
except ValueError as error:
    raise AssertionError(
        "analytics 任务必须路由到 Analytics Agent"
    ) from error

assert isinstance(analytics_task, TaskBrief)
assert analytics_task.task_type == "analytics"
assert analytics_task.objective == "分析广告表现"
assert analytics_task.context == (
    "展示 10000；点击 300；转化 12；目标：增加转化"
)
assert analytics_task.assigned_agent == "Analytics Agent"

analytics_agent = object()
received_requests = []


def run_analytics(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "摘要：CTR 3%；问题：缺少成本数据；"
        "建议：补充花费后评估 CPA。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        analytics_agent=analytics_agent,
        run_analytics=run_analytics,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Analytics Agent"
    ) from error

completed = execute_task(analytics_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Analytics Agent"
assert completed.output == (
    "摘要：CTR 3%；问题：缺少成本数据；"
    "建议：补充花费后评估 CPA。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is analytics_agent
assert analytics_task.objective in received_requests[0][1]
assert analytics_task.context in received_requests[0][1]

print("Analytics-agent tests passed.")
