from client_project_workflow import (
    run_client_project_workflow,
)


called_agents = []


def research_handler(task):
    called_agents.append(task.assigned_agent)
    return "Research 完成"


def strategy_handler(task):
    called_agents.append(task.assigned_agent)
    raise RuntimeError("Strategy 暂时不可用")


def forbidden_project_handler(task):
    raise AssertionError(
        "Strategy 失败后不得调用项目管理 Agent"
    )


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": research_handler,
        "Strategy Agent": strategy_handler,
        "Client Project Manager Agent": (
            forbidden_project_handler
        ),
    },
)

assert result.status == "failed"
assert result.final_output == ""
assert result.error == (
    "Strategy Agent: Strategy 暂时不可用"
)
assert [step.status for step in result.steps] == [
    "completed",
    "failed",
]
assert called_agents == [
    "Search Agent",
    "Strategy Agent",
]

print("Client-project-workflow failure tests passed.")
