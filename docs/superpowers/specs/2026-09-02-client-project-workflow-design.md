# Day041 Client Project Workflow Design

## Goal

Create the first explicit multi-agent workflow for a client project:

`Search Agent -> Strategy Agent -> Client Project Manager Agent`

The workflow must reuse the existing `TaskBrief`, task router, task executor,
agent handlers, and `AgentResult` contract.

## Scope

The workflow starts only from this command:

```text
工作流：client_project | 目标 | 项目背景
```

Day041 does not add parallel execution, a general DAG engine, persistent
workflow state, automatic retries, automatic intent detection, or external
project-management integrations.

## Contract

`workflow_contract.py` defines `WorkflowResult` with:

- `workflow_id`
- `workflow_type`
- `status`
- `steps: list[AgentResult]`
- `final_output`
- `error`

A completed workflow uses the Client Project Manager output as
`final_output`. A failed workflow returns an empty `final_output`, preserves
all attempted step results, and reports the failing step through `error`.

## Components

### `client_project_workflow.py`

Provide `run_client_project_workflow(objective, context, handlers)`.

It creates and executes three tasks sequentially through the existing
`route_task()` and `execute_task()` functions:

1. Route the original objective and context to `research`.
2. Route the original context plus the labeled Research output to `strategy`.
3. Route the original context plus labeled Research and Strategy outputs to
   `client_management`.

Each handoff is plain text with explicit labels. There is no shared mutable
workflow state.

### `workflow_entry.py`

Parse the explicit workflow command and dispatch only `client_project`.

- Return no match for input without the `工作流：` prefix.
- Reject malformed commands, blank required values, and unknown workflow
  types with `ValueError`.
- Return a `WorkflowResult` for a valid command.

### `main.py`

Recognize `工作流：` before the existing single-task and ordinary-chat paths.
Pass the existing `task_handlers` to the workflow entry and print either the
final project plan or a clear failure message.

## Failure Behavior

Use fail-fast execution:

- Stop immediately when any step returns `status="failed"`.
- Do not call later Agent handlers.
- Preserve completed and failed `AgentResult` objects in execution order.
- Do not retry automatically; the existing Search service remains responsible
  for its own bounded retry behavior.

## Testing

Add four focused tests:

1. Successful three-step execution, structured result, and explicit handoffs.
2. Fail-fast behavior and proof that later handlers are not called.
3. Workflow command parsing, validation, and dispatch.
4. Main wiring and precedence over ordinary Agent conversation.

All tests inject fake handlers and must not call external APIs. Add the three
new source files to `verify_project.py`. Expected full verification after
implementation: 38/38 tests passed.
