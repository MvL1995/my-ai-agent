from task_factory import create_task


TASK_ROUTES = {
    "research": "Search Agent",
    "strategy": "Strategy Agent",
    "copywriting": "Copywriting Agent",
}


def route_task(task_type, objective, context):
    normalized_type = task_type.strip().lower()
    assigned_agent = TASK_ROUTES.get(normalized_type)

    if assigned_agent is None:
        raise ValueError(
            f"Unsupported task type: {normalized_type}"
        )

    return create_task(
        normalized_type,
        objective,
        context,
        assigned_agent,
    )
