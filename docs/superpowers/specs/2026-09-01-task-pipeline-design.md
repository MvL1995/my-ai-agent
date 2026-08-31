# Day030 Task Pipeline Design

## Goal

Provide one application-facing function that routes and executes a specialist task.

## Public Interface

`task_pipeline.py` provides:

```python
run_task_pipeline(
    task_type,
    objective,
    context,
    handlers,
) -> AgentResult
```

## Behavior

- Call `route_task()` to validate inputs, select the specialist, and create the `TaskBrief`.
- Call `execute_task()` with that task and the supplied handler registry.
- Return the resulting `AgentResult` unchanged.
- Preserve routing and execution errors from the existing components.

## Constraints

- Reuse `task_router.py` and `task_executor.py` without duplicating their logic.
- Do not construct Agents or search services inside the pipeline.
- Do not modify `main.py` during Day030.
- Add no dependencies or framework abstractions.

## Testing

Verify complete routing and dispatch, success and specialist-failure results, unsupported task rejection, and missing-handler rejection.
