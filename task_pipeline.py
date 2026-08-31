from task_executor import execute_task
from task_router import route_task


def run_task_pipeline(
    task_type,
    objective,
    context,
    handlers,
):
    task = route_task(
        task_type,
        objective,
        context,
    )
    return execute_task(task, handlers)
