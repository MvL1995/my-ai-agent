# Day031 Main Agent Task Entry Design

## Goal

Let the interactive Main Agent accept an explicit specialist task command and run it through the Day030 Task Pipeline.

## Command

```text
任务：research | 研究吉隆坡餐饮市场 | 客户准备推出午餐套餐
```

The three required fields are task type, objective, and context.

## Components

`task_entry.py` provides:

```python
extract_task_request(user_input)
execute_task_request(user_input, handlers)
```

`main.py` builds the handler registry once and passes explicit task commands to `execute_task_request()`.

## Behavior

- Non-task messages return `None` and continue through the existing Main Agent flow.
- Valid task commands are trimmed, routed, executed, and returned as `AgentResult` values.
- Malformed task commands raise `ValueError` with a usage message.
- Completed results are printed under the specialist Agent name.
- Failed results are printed by Main Agent using the standardized error message.

## Constraints

- Only explicit `任务：` commands trigger specialist dispatch.
- Reuse `build_agent_handlers()` and `run_task_pipeline()`.
- Keep the existing search, memory, session, and approval flows unchanged.
- Add no dependencies and no autonomous task inference.

## Testing

Verify command parsing and execution separately from the interactive-loop wiring, then run the complete regression suite.
