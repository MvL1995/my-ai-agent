from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    sales_task = route_task(
        "  SaLeS  ",
        "  制定餐厅网站销售方案  ",
        "  潜在客户：本地餐厅；需求：增加线上预订  ",
    )
except ValueError as error:
    raise AssertionError(
        "sales 任务必须路由到 Sales Agent"
    ) from error

assert isinstance(sales_task, TaskBrief)
assert sales_task.task_type == "sales"
assert sales_task.objective == "制定餐厅网站销售方案"
assert sales_task.context == (
    "潜在客户：本地餐厅；需求：增加线上预订"
)
assert sales_task.assigned_agent == "Sales Agent"

sales_agent = object()
received_requests = []


def run_sales(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "资格：需求明确；价值主张：提升线上预订路径；"
        "下一步：确认预算和决策人。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        sales_agent=sales_agent,
        run_sales=run_sales,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Sales Agent"
    ) from error

completed = execute_task(sales_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Sales Agent"
assert completed.output == (
    "资格：需求明确；价值主张：提升线上预订路径；"
    "下一步：确认预算和决策人。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is sales_agent
assert sales_task.objective in received_requests[0][1]
assert sales_task.context in received_requests[0][1]

print("Sales-agent tests passed.")
