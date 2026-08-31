# Day026 Task Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create validated `TaskBrief` objects with unique task IDs.

**Architecture:** A focused `task_factory.py` converts cleaned input strings into the existing `TaskBrief` contract. It has no database or Main Agent dependency.

**Tech Stack:** Python standard library, `uuid4`, existing script-based tests.

**Spec:** `docs/superpowers/specs/2026-09-01-task-factory-design.md`

## Global Constraints

- Use only the Python standard library.
- Return the existing `TaskBrief`.
- Reject empty required text with `ValueError`.
- Do not modify `main.py` during Day026.

---

### Task 1: Build the Task Factory

**Files:**
- Create: `task_factory.py`
- Create: `test_task_factory.py`
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `TaskBrief` from `task_contract.py`
- Produces: `create_task(task_type, objective, context, assigned_agent) -> TaskBrief`

- [ ] **Step 1: Write the failing test**

Create `test_task_factory.py`:

```python
import importlib.util

module_spec = importlib.util.find_spec("task_factory")

assert module_spec is not None, "task_factory.py 尚未实现"

from task_contract import TaskBrief
from task_factory import create_task


first_task = create_task(
    "research",
    "  研究客户市场  ",
    "  客户经营本地餐厅  ",
    "  Search Agent  ",
)

second_task = create_task(
    "research",
    "研究竞争对手",
    "客户经营本地餐厅",
    "Search Agent",
)

assert isinstance(first_task, TaskBrief)
assert first_task.task_id.startswith("task-")
assert first_task.task_id != second_task.task_id
assert first_task.objective == "研究客户市场"
assert first_task.context == "客户经营本地餐厅"
assert first_task.assigned_agent == "Search Agent"

invalid_inputs = (
    ("", "目标", "背景", "Search Agent"),
    ("research", " ", "背景", "Search Agent"),
    ("research", "目标", "", "Search Agent"),
    ("research", "目标", "背景", " "),
)

for arguments in invalid_inputs:
    try:
        create_task(*arguments)
    except ValueError:
        pass
    else:
        raise AssertionError("空白必填字段必须触发 ValueError")

print("Task-factory tests passed.")
```

- [ ] **Step 2: Verify the test fails**

Run:

```powershell
python test_task_factory.py
```

Expected:

```text
AssertionError: task_factory.py 尚未实现
```

- [ ] **Step 3: Write the minimal implementation**

Create `task_factory.py`:

```python
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
```

- [ ] **Step 4: Verify the focused test passes**

Run:

```powershell
python test_task_factory.py
```

Expected:

```text
Task-factory tests passed.
```

- [ ] **Step 5: Add the source file to verification**

Add this entry to `SOURCE_FILE_NAMES` in `verify_project.py`:

```python
    "task_factory.py",
```

- [ ] **Step 6: Run complete verification and checkpoint**

Run:

```powershell
python checkpoint_project.py
```

Expected:

```text
[PASS] compile task_factory.py
[PASS] test_task_factory.py
Summary: 19/19 tests passed.
Checkpoint created: ...
```

- [ ] **Step 7: Record completion**

Add to `PROGRESS.md`:

```markdown
## Day026 — Complete

- Added `create_task()` for validated task creation.
- Added unique task IDs using `uuid4()`.
- Added whitespace cleanup and required-field validation.
- Added `test_task_factory.py`.
- Verification: `python checkpoint_project.py` — 19/19 tests passed.
```