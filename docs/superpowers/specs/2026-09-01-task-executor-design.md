# Day028 Task Executor Design

## Goal

Execute an existing `TaskBrief` with its assigned specialist handler and return a standard `AgentResult`.

## Public Interface

`task_executor.py` provides:

```python
execute_task(task, handlers) -> AgentResult
```

`handlers` maps an `assigned_agent` name to a callable. Each handler receives the complete `TaskBrief` and returns its text output.

## Behavior

- Select the handler using `task.assigned_agent`.
- Pass the original `TaskBrief` to that handler.
- On success, return an `AgentResult` with status `completed`.
- If the specialist handler raises an exception, return an `AgentResult` with status `failed` and the error message.
- If no handler is registered for the assigned Agent, raise `ValueError` because the executor configuration is invalid.

## Constraints

- Reuse `TaskBrief` and `AgentResult` from `task_contract.py`.
- Keep the executor independent of the Agents SDK, network services, and databases.
- Do not modify `main.py` during Day028.
- Do not add dependencies or new abstraction layers.

## Testing

Verify exact task dispatch, successful result fields, specialist failure conversion, and rejection of an unregistered Agent.
