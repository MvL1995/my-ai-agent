# Day029 Agent Handler Registry Design

## Goal

Connect the existing Search Agent to the Day028 task executor through a small handler registry.

## Public Interface

`agent_registry.py` provides:

```python
build_agent_handlers(search_agent, cache=None, run_search=None) -> dict
```

The returned registry maps `"Search Agent"` to a callable that accepts one `TaskBrief` and returns text.

## Behavior

- Build the search query from `task.objective` and `task.context`.
- Reuse `execute_search()` for safety checks, retries, validation, audit, and caching.
- Return the validated search message when search completes.
- Raise `RuntimeError` for non-completed search outcomes so `execute_task()` converts the failure into an `AgentResult`.

## Constraints

- Reuse the existing Search Agent and search service.
- Keep the registry independent of the interactive loop.
- Do not modify `main.py` during Day029.
- Add no dependencies and no general plugin framework.

## Testing

Verify registration, complete TaskBrief delivery, successful `AgentResult`, and failed-search conversion through the real Task Executor boundary.
