from time import perf_counter

from task_contract import AgentResult


def execute_task(task, handlers):
    handler = handlers.get(task.assigned_agent)

    if handler is None:
        raise ValueError(
            f"Unregistered agent: {task.assigned_agent}"
        )

    started_at = perf_counter()
    try:
        output = handler(task)
    except Exception as error:
        return AgentResult(
            task_id=task.task_id,
            agent_name=task.assigned_agent,
            status="failed",
            output="",
            error=str(error),
            duration_ms=(perf_counter() - started_at) * 1000,
        )

    return AgentResult(
        task_id=task.task_id,
        agent_name=task.assigned_agent,
        status="completed",
        output=output,
        duration_ms=(perf_counter() - started_at) * 1000,
    )
