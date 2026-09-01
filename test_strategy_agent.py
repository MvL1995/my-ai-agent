from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    strategy_task = route_task(
        "  StRaTeGy  ",
        "  制定客户获客策略  ",
        "  客户经营吉隆坡本地餐厅  ",
    )
except ValueError as error:
    raise AssertionError(
        "strategy 任务必须路由到 Strategy Agent"
    ) from error

assert isinstance(strategy_task, TaskBrief)
assert strategy_task.task_type == "strategy"
assert strategy_task.objective == "制定客户获客策略"
assert strategy_task.context == "客户经营吉隆坡本地餐厅"
assert strategy_task.assigned_agent == "Strategy Agent"

strategy_agent = object()
received_requests = []


def run_strategy(received_agent, request):
    received_requests.append((received_agent, request))
    return "渠道：短视频；行动：测试两组午餐广告。"


try:
    handlers = build_agent_handlers(
        object(),
        strategy_agent=strategy_agent,
        run_strategy=run_strategy,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Strategy Agent"
    ) from error

completed = execute_task(strategy_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Strategy Agent"
assert completed.output == (
    "渠道：短视频；行动：测试两组午餐广告。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is strategy_agent
assert strategy_task.objective in received_requests[0][1]
assert strategy_task.context in received_requests[0][1]

print("Strategy-agent tests passed.")
