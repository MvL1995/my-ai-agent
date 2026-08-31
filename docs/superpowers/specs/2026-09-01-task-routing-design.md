# Day027 Task Routing Design

## Goal

Route a task type to the correct specialist Agent and return a validated
`TaskBrief` through the existing Task Factory.

## Component

`task_router.py` owns the task-type-to-agent mapping and provides
`route_task()`.

## Interface

```python
route_task(task_type, objective, context) -> TaskBrief
```

## Behavior

- Normalize `task_type` by trimming whitespace and converting it to lowercase.
- Route `research` tasks to `Search Agent`.
- Delegate TaskBrief construction and required-field validation to
  `task_factory.create_task()`.
- Reject an unsupported task type with `ValueError`.
- Keep routing independent from `main.py` during Day027.

## Constraints

- Reuse `TaskBrief` and `create_task()`.
- Use only the Python standard library and existing project modules.
- Do not instantiate or execute Agents in the router.
- Keep the route table explicit and easy to extend.

## Testing

- A research task is assigned to `Search Agent`.
- Task type matching ignores surrounding whitespace and letter case.
- The returned value is a `TaskBrief` with cleaned fields.
- Unsupported and blank task types raise `ValueError`.
- Full project verification remains green.
