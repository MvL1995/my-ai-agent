# Day027 Task Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route supported task types to specialist Agent names and return validated `TaskBrief` objects.

**Architecture:** A focused `task_router.py` owns a small explicit route table. Its `route_task()` function normalizes the task type, selects the specialist name, and delegates object construction and validation to the existing `create_task()` factory.

**Tech Stack:** Python 3, standard library, existing `task_contract.py` and `task_factory.py`

**Spec:** `docs/superpowers/specs/2026-09-01-task-routing-design.md`

## Global Constraints

- Reuse `TaskBrief` and `create_task()`.
- Add no third-party dependency.
- Do not instantiate or execute Agents in the router.
- Do not modify `main.py` during Day027.

---

### Task 1: Build and verify the task router

**Files:**
- Create: `test_task_router.py`
- Create: `task_router.py`
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `create_task(task_type, objective, context, assigned_agent) -> TaskBrief`
- Produces: `route_task(task_type, objective, context) -> TaskBrief`

- [x] **Step 1: Write the failing test**

Create `test_task_router.py`:

```python
import importlib.util

module_spec = importlib.util.find_spec("task_router")

assert module_spec is not None, "task_router.py 尚未实现"

from task_contract import TaskBrief
from task_router import route_task


research_task = route_task(
    "  ReSeArCh  ",
    "  研究客户市场  ",
    "  客户经营本地餐厅  ",
)

assert isinstance(research_task, TaskBrief)
assert research_task.task_type == "research"
assert research_task.objective == "研究客户市场"
assert research_task.context == "客户经营本地餐厅"
assert research_task.assigned_agent == "Search Agent"

for unsupported_type in ("", " ", "strategy"):
    try:
        route_task(unsupported_type, "目标", "背景")
    except ValueError:
        pass
    else:
        raise AssertionError("未知或空白任务类型必须触发 ValueError")

print("Task-router tests passed.")
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python test_task_router.py
```

Expected: `AssertionError: task_router.py 尚未实现`

- [x] **Step 3: Write the minimal implementation**

Create `task_router.py`:

```python
from task_factory import create_task


TASK_ROUTES = {
    "research": "Search Agent",
}


def route_task(task_type, objective, context):
    normalized_type = task_type.strip().lower()
    assigned_agent = TASK_ROUTES.get(normalized_type)

    if assigned_agent is None:
        raise ValueError(f"Unsupported task type: {normalized_type}")

    return create_task(
        normalized_type,
        objective,
        context,
        assigned_agent,
    )
```

- [x] **Step 4: Run the focused test and verify GREEN**

Run:

```powershell
python test_task_router.py
```

Expected: `Task-router tests passed.`

- [x] **Step 5: Add the router to project verification**

Add this entry to `SOURCE_FILE_NAMES` in `verify_project.py`:

```python
"task_router.py",
```

- [x] **Step 6: Record Day027 completion**

Append to `PROGRESS.md`:

```markdown
## Day027 — Complete

- Added explicit task-type routing in `task_router.py`.
- Routed `research` tasks to `Search Agent`.
- Reused `create_task()` for validation and TaskBrief creation.
- Added `test_task_router.py`.
- Verification: `python checkpoint_project.py` — 20/20 tests passed.
```

- [x] **Step 7: Run complete verification and checkpoint**

Run:

```powershell
python checkpoint_project.py
```

Expected:

```text
[PASS] compile task_router.py
[PASS] test_task_router.py
Summary: 20/20 tests passed.
Checkpoint created: ...
```

- [x] **Step 8: Commit Day027 files**

Stage only the Day027 files and shared verification/progress files, then commit:

```powershell
git add docs/superpowers/specs/2026-09-01-task-routing-design.md docs/superpowers/plans/2026-09-01-task-routing-implementation.md task_router.py test_task_router.py verify_project.py PROGRESS.md
git commit -m "feat: add Day027 task routing"
```
