from uuid import uuid4

from task_contract import TaskBrief


def _clean_required(field_name, value):
    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return cleaned_value


def create_task(
    task_type,
    objective,
    context,
    assigned_agent,
):
    return TaskBrief(
        task_id=f"task-{uuid4().hex}",
        task_type=_clean_required("task_type", task_type),
        objective=_clean_required("objective", objective),
        context=_clean_required("context", context),
        assigned_agent=_clean_required(
            "assigned_agent",
            assigned_agent,
        ),
    )