from client_project_workflow import (
    run_client_project_workflow,
)


called_agents = []


def completed_handler(task):
    called_agents.append(task.assigned_agent)
    return f"{task.assigned_agent} 完成"


def coding_handler(task):
    called_agents.append(task.assigned_agent)
    raise RuntimeError("Coding 暂时不可用")


def forbidden_handler(task):
    raise AssertionError(
        "Coding 失败后不得调用下游 Agent"
    )


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": completed_handler,
        "Strategy Agent": completed_handler,
        "Copywriting Agent": completed_handler,
        "Web Design Agent": completed_handler,
        "Coding Agent": coding_handler,
        "QA Agent": forbidden_handler,
        "Client Project Manager Agent": (
            forbidden_handler
        ),
    },
)

assert result.status == "failed"
assert result.final_output == ""
assert result.error == (
    "Coding Agent: Coding 暂时不可用"
)
assert [step.status for step in result.steps] == [
    "completed",
    "completed",
    "completed",
    "completed",
    "failed",
]
assert called_agents == [
    "Search Agent",
    "Strategy Agent",
    "Copywriting Agent",
    "Web Design Agent",
    "Coding Agent",
]

print("Client-project-workflow failure tests passed.")
