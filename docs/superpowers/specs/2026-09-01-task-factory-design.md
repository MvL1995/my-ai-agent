# Day026 Task Factory Design

## Goal

Create validated `TaskBrief` objects for future specialist-agent routing.

## Component

`task_factory.py` provides `create_task()`.

## Behavior

- Generate a unique task ID with `uuid4()`.
- Trim text inputs.
- Reject empty required values with `ValueError`.
- Return a `TaskBrief`.
- Do not modify `main.py` during Day026.

## Testing

Test valid creation, unique IDs, and empty-input rejection.