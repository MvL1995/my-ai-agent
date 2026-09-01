from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    web_design_task = route_task(
        "  WeB_DeSiGn  ",
        "  设计餐厅落地页  ",
        "  吉隆坡上班族，午餐套餐 RM15  ",
    )
except ValueError as error:
    raise AssertionError(
        "web_design 任务必须路由到 Web Design Agent"
    ) from error

assert isinstance(web_design_task, TaskBrief)
assert web_design_task.task_type == "web_design"
assert web_design_task.objective == "设计餐厅落地页"
assert web_design_task.context == "吉隆坡上班族，午餐套餐 RM15"
assert web_design_task.assigned_agent == "Web Design Agent"

web_design_agent = object()
received_requests = []


def run_web_design(received_agent, request):
    received_requests.append((received_agent, request))
    return "页面：Hero、套餐、评价、CTA；移动端优先。"


try:
    handlers = build_agent_handlers(
        object(),
        web_design_agent=web_design_agent,
        run_web_design=run_web_design,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Web Design Agent"
    ) from error

completed = execute_task(web_design_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Web Design Agent"
assert completed.output == (
    "页面：Hero、套餐、评价、CTA；移动端优先。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is web_design_agent
assert web_design_task.objective in received_requests[0][1]
assert web_design_task.context in received_requests[0][1]

print("Web-design-agent tests passed.")
