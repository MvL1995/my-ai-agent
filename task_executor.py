from task_contract import AgentResult


def execute_task(task, handlers):
    handler = handlers.get(task.assigned_agent)

    if handler is None:
        raise ValueError(
            f"Unregistered agent: {task.assigned_agent}"
        )

    try:
        output = handler(task)
    except Exception as error:
        return AgentResult(
            task_id=task.task_id,
            agent_name=task.assigned_agent,
            status="failed",
            output="",
            error=str(error),
        )

    return AgentResult(
        task_id=task.task_id,
        agent_name=task.assigned_agent,
        status="completed",
        output=output,
    )
