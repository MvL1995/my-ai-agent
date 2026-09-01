from task_contract import TaskBrief
from task_executor import execute_task
from agent_registry import build_agent_handlers
from task_router import route_task


try:
    project_task = route_task(
        "  ClIeNt_MaNaGeMeNt  ",
        "  规划餐厅网站交付项目  ",
        "  客户已确认首页、菜单页和预订页；目标：两周内提交初稿  ",
    )
except ValueError as error:
    raise AssertionError(
        "client_management 任务必须路由到 Client Project Manager Agent"
    ) from error

assert isinstance(project_task, TaskBrief)
assert project_task.task_type == "client_management"
assert project_task.objective == "规划餐厅网站交付项目"
assert project_task.context == (
    "客户已确认首页、菜单页和预订页；目标：两周内提交初稿"
)
assert project_task.assigned_agent == "Client Project Manager Agent"

project_agent = object()
received_requests = []


def run_client_management(received_agent, request):
    received_requests.append((received_agent, request))
    return (
        "范围：首页、菜单页和预订页；"
        "建议里程碑：第 7 天完成设计稿；"
        "下一步：确认内容负责人。"
    )


try:
    handlers = build_agent_handlers(
        object(),
        client_management_agent=project_agent,
        run_client_management=run_client_management,
    )
except TypeError as error:
    raise AssertionError(
        "agent registry 必须支持 Client Project Manager Agent"
    ) from error

completed = execute_task(project_task, handlers)

assert completed.status == "completed"
assert completed.agent_name == "Client Project Manager Agent"
assert completed.output == (
    "范围：首页、菜单页和预订页；"
    "建议里程碑：第 7 天完成设计稿；"
    "下一步：确认内容负责人。"
)
assert completed.error is None
assert len(received_requests) == 1
assert received_requests[0][0] is project_agent
assert project_task.objective in received_requests[0][1]
assert project_task.context in received_requests[0][1]

print("Client-project-management-agent tests passed.")
