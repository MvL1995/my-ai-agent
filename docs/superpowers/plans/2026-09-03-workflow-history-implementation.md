# Day043 Workflow History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every completed or failed client-project workflow, reject sensitive workflow content, and expose a minimal recent-history command.

**Architecture:** Add one `workflow_history.py` persistence boundary backed by a new `workflow_runs` table in the existing `long_term_memory.db`. `workflow_entry.execute_workflow_request()` validates input, runs the workflow, saves exactly once, and returns the unchanged `WorkflowResult`; `main.py` initializes storage and lists recent summaries.

**Tech Stack:** Python standard library (`sqlite3`, `json`, `dataclasses`, `tempfile`), existing assertion-style tests, existing checkpoint verifier.

**Spec:** `docs/superpowers/specs/2026-09-03-workflow-history-design.md`

## Global Constraints

- Reuse `long_term_memory.db`; do not modify existing memory tables.
- Do not change `WorkflowResult` or `AgentResult`.
- Use only the Python standard library and existing project modules.
- Reject passwords, API keys, tokens, and secrets with the existing `contains_sensitive_memory()` guard.
- Persist one atomic row per attempted workflow, including failed workflows.
- Do not add filters, editing, deletion, replay, encryption, or a Web UI.

---

### Task 1: Build the Workflow-History Store

**Files:**
- Create: `workflow_history.py`
- Create: `test_workflow_history.py`

**Interfaces:**
- Consumes: `memory.DB_PATH`, `memory.contains_sensitive_memory(content)`, `WorkflowResult`, and its ordered `AgentResult` values.
- Produces: `init_workflow_history_db()`, `save_workflow_run(objective, context, result)`, `get_workflow_history(limit=10)`, and `get_workflow_run(workflow_id)`.

- [ ] **Step 1: Write the failing module and schema test**

Create `test_workflow_history.py` with the import guard and temporary database setup:

```python
import importlib.util
import os
import tempfile

module_spec = importlib.util.find_spec("workflow_history")
assert module_spec is not None, "workflow_history.py 尚未实现"

import workflow_history
from task_contract import AgentResult
from workflow_contract import WorkflowResult


original_db_path = workflow_history.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    workflow_history.DB_PATH = os.path.join(
        temp_dir,
        "test_memory.db",
    )

    try:
        workflow_history.init_workflow_history_db()

        completed = WorkflowResult(
            workflow_id="workflow-completed",
            workflow_type="client_project",
            status="completed",
            steps=[
                AgentResult(
                    "task-research",
                    "Search Agent",
                    "completed",
                    "Research 完成",
                ),
                AgentResult(
                    "task-strategy",
                    "Strategy Agent",
                    "completed",
                    "Strategy 完成",
                ),
                AgentResult(
                    "task-project",
                    "Client Project Manager Agent",
                    "completed",
                    "项目计划完成",
                ),
            ],
            final_output="项目计划完成",
        )

        workflow_history.save_workflow_run(
            "启动餐厅项目",
            "吉隆坡本地餐厅",
            completed,
        )

        stored = workflow_history.get_workflow_run(
            "workflow-completed"
        )
        assert stored["objective"] == "启动餐厅项目"
        assert stored["context"] == "吉隆坡本地餐厅"
        assert stored["status"] == "completed"
        assert stored["final_output"] == "项目计划完成"
        assert [step["agent_name"] for step in stored["steps"]] == [
            "Search Agent",
            "Strategy Agent",
            "Client Project Manager Agent",
        ]
    finally:
        workflow_history.DB_PATH = original_db_path
```

- [ ] **Step 2: Run the new test and verify the expected failure**

Run:

```powershell
python test_workflow_history.py
```

Expected: FAIL because `workflow_history.py` or its public functions do not yet exist.

- [ ] **Step 3: Implement the minimal schema and complete-run storage**

Create `workflow_history.py`:

```python
import json
import sqlite3
from dataclasses import asdict

from memory import (
    DB_PATH,
    contains_sensitive_memory,
)


SENSITIVE_WORKFLOW_ERROR = (
    "拒绝工作流：检测到密码、API Key、Token 或密钥。"
)


def init_workflow_history_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                workflow_id TEXT PRIMARY KEY,
                workflow_type TEXT NOT NULL,
                objective TEXT NOT NULL,
                context TEXT NOT NULL,
                status TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                final_output TEXT NOT NULL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_workflow_run(objective, context, result):
    persisted_text = [
        objective,
        context,
        result.final_output,
        result.error or "",
    ]
    for step in result.steps:
        persisted_text.extend([
            step.output,
            step.error or "",
        ])

    if any(
        contains_sensitive_memory(value)
        for value in persisted_text
    ):
        raise ValueError(SENSITIVE_WORKFLOW_ERROR)

    try:
        steps_json = json.dumps(
            [asdict(step) for step in result.steps],
            ensure_ascii=False,
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO workflow_runs (
                    workflow_id,
                    workflow_type,
                    objective,
                    context,
                    status,
                    steps_json,
                    final_output,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.workflow_id,
                    result.workflow_type,
                    objective,
                    context,
                    result.status,
                    steps_json,
                    result.final_output,
                    result.error,
                ),
            )
    except (sqlite3.Error, TypeError) as error:
        raise RuntimeError(
            "工作流已执行，但历史保存失败。"
        ) from error
```

- [ ] **Step 4: Add full and summary query implementations**

Append to `workflow_history.py`:

```python
def get_workflow_history(limit=10):
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer.")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                created_at,
                workflow_id,
                workflow_type,
                status,
                objective
            FROM workflow_runs
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "created_at": row[0],
            "workflow_id": row[1],
            "workflow_type": row[2],
            "status": row[3],
            "objective": row[4],
        }
        for row in rows
    ]


def get_workflow_run(workflow_id):
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty.")

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT
                workflow_id,
                workflow_type,
                objective,
                context,
                status,
                steps_json,
                final_output,
                error,
                created_at
            FROM workflow_runs
            WHERE workflow_id = ?
            """,
            (workflow_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "workflow_id": row[0],
        "workflow_type": row[1],
        "objective": row[2],
        "context": row[3],
        "status": row[4],
        "steps": json.loads(row[5]),
        "final_output": row[6],
        "error": row[7],
        "created_at": row[8],
    }
```

- [ ] **Step 5: Extend the test for failed runs, ordering, limits, sensitive output, duplicate IDs, and missing IDs**

Inside the temporary-database `try` block in `test_workflow_history.py`, after the completed-run assertions, add:

```python
        failed = WorkflowResult(
            workflow_id="workflow-failed",
            workflow_type="client_project",
            status="failed",
            steps=[
                AgentResult(
                    "task-research-failed",
                    "Search Agent",
                    "failed",
                    "",
                    "search unavailable",
                )
            ],
            final_output="",
            error="Search Agent: search unavailable",
        )
        workflow_history.save_workflow_run(
            "失败项目",
            "测试背景",
            failed,
        )

        stored_failed = workflow_history.get_workflow_run(
            "workflow-failed"
        )
        assert stored_failed["status"] == "failed"
        assert len(stored_failed["steps"]) == 1
        assert stored_failed["error"] == (
            "Search Agent: search unavailable"
        )

        recent = workflow_history.get_workflow_history(limit=1)
        assert len(recent) == 1
        assert recent[0]["workflow_id"] == "workflow-failed"
        assert workflow_history.get_workflow_run("missing") is None

        try:
            workflow_history.get_workflow_history(limit=0)
        except ValueError:
            pass
        else:
            raise AssertionError("非正数 limit 必须被拒绝")

        try:
            workflow_history.get_workflow_run(" ")
        except ValueError:
            pass
        else:
            raise AssertionError("空 workflow_id 必须被拒绝")

        try:
            workflow_history.save_workflow_run(
                "重复项目",
                "重复背景",
                completed,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("重复 workflow_id 必须失败")

        sensitive = WorkflowResult(
            workflow_id="workflow-sensitive",
            workflow_type="client_project",
            status="completed",
            steps=[
                AgentResult(
                    "task-sensitive",
                    "Search Agent",
                    "completed",
                    "API Key: secret",
                )
            ],
            final_output="敏感输出",
        )
        try:
            workflow_history.save_workflow_run(
                "敏感项目",
                "测试背景",
                sensitive,
            )
        except ValueError as error:
            assert str(error) == (
                workflow_history.SENSITIVE_WORKFLOW_ERROR
            )
        else:
            raise AssertionError("敏感输出不得保存")

        assert workflow_history.get_workflow_run(
            "workflow-sensitive"
        ) is None

print("Workflow-history tests passed.")
```

- [ ] **Step 6: Run the storage test**

Run:

```powershell
python test_workflow_history.py
```

Expected: `Workflow-history tests passed.`

- [ ] **Step 7: Commit the independently working store**

```powershell
git add workflow_history.py test_workflow_history.py
git commit -m "feat: add workflow history store"
```

---

### Task 2: Persist Runs at the Workflow Entry Boundary

**Files:**
- Modify: `workflow_entry.py`
- Modify: `test_workflow_entry.py`

**Interfaces:**
- Consumes: `contains_sensitive_memory(content)`, `save_workflow_run(objective, context, result)`, and the existing `run_workflow(objective, context, handlers)` callable.
- Produces: `execute_workflow_request(user_input, handlers, run_workflow=..., save_run=...)` that rejects sensitive input, saves exactly once, and returns the same result object.

- [ ] **Step 1: Extend the entry test with an injected saver**

In `test_workflow_entry.py`, add `saved = {}` beside `received = {}` and add:

```python
def fake_save(objective, context, result):
    saved["objective"] = objective
    saved["context"] = context
    saved["result"] = result
```

Pass `save_run=fake_save` to the existing `execute_workflow_request()` call, then add:

```python
assert saved == {
    "objective": "启动客户项目",
    "context": "餐厅客户",
    "result": result,
}
```

- [ ] **Step 2: Add sensitive-input and exactly-once assertions**

Append to `test_workflow_entry.py` before the final print:

```python
calls = {"run": 0, "save": 0}


def counting_workflow(objective, context, handlers):
    calls["run"] += 1
    return fake_workflow(objective, context, handlers)


def counting_save(objective, context, result):
    calls["save"] += 1


counted_result = execute_workflow_request(
    "客户项目：启动客户项目 | 普通背景",
    handlers,
    run_workflow=counting_workflow,
    save_run=counting_save,
)
assert counted_result.final_output == "客户项目计划"
assert calls == {"run": 1, "save": 1}

for sensitive_input in (
    "客户项目：保存 API Key | 普通背景",
    "客户项目：普通目标 | password=secret",
):
    try:
        execute_workflow_request(
            sensitive_input,
            handlers,
            run_workflow=counting_workflow,
            save_run=counting_save,
        )
    except ValueError as error:
        assert "拒绝工作流" in str(error)
    else:
        raise AssertionError("敏感工作流输入必须被拒绝")

assert calls == {"run": 1, "save": 1}
```

- [ ] **Step 3: Run the entry test and verify it fails**

Run:

```powershell
python test_workflow_entry.py
```

Expected: FAIL because `execute_workflow_request()` does not accept `save_run` and does not guard sensitive workflow input.

- [ ] **Step 4: Implement the minimal entry integration**

Update the imports in `workflow_entry.py`:

```python
from memory import contains_sensitive_memory
from workflow_history import (
    SENSITIVE_WORKFLOW_ERROR,
    save_workflow_run,
)
```

Replace `execute_workflow_request()` with:

```python
def execute_workflow_request(
    user_input,
    handlers,
    run_workflow=run_client_project_workflow,
    save_run=save_workflow_run,
):
    request = extract_workflow_request(user_input)

    if request is None:
        return None

    _, objective, context = request

    if (
        contains_sensitive_memory(objective)
        or contains_sensitive_memory(context)
    ):
        raise ValueError(SENSITIVE_WORKFLOW_ERROR)

    result = run_workflow(
        objective,
        context,
        handlers,
    )
    save_run(objective, context, result)
    return result
```

- [ ] **Step 5: Run focused integration tests**

Run:

```powershell
python test_workflow_entry.py
python test_workflow_history.py
python test_client_project_workflow.py
```

Expected:

```text
Workflow-entry tests passed.
Workflow-history tests passed.
Client-project-workflow tests passed.
```

- [ ] **Step 6: Commit the workflow boundary integration**

```powershell
git add workflow_entry.py test_workflow_entry.py
git commit -m "feat: persist client workflow runs"
```

---

### Task 3: Initialize Storage, Show Recent History, and Verify the Project

**Files:**
- Modify: `main.py`
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `init_workflow_history_db()` and `get_workflow_history(limit=10)`.
- Produces: the exact local command `查看项目记录`, startup table initialization, and graceful `RuntimeError` reporting for failed persistence.

- [ ] **Step 1: Add workflow-history imports and startup initialization**

In `main.py`, after the `workflow_entry` import, add:

```python
from workflow_history import (
    get_workflow_history,
    init_workflow_history_db,
)
```

Immediately after `init_memory_db()`, add:

```python
init_workflow_history_db()
```

- [ ] **Step 2: Add the minimal recent-history command**

Inside the main loop, immediately after the exit check and before search routing, add:

```python
    if user_input == "查看项目记录":
        runs = get_workflow_history(limit=10)
        print("\n最近客户项目记录：")

        if not runs:
            print("- 暂无项目记录")
        else:
            for run in runs:
                print(
                    f'- {run["created_at"]} | '
                    f'{run["workflow_id"]} | '
                    f'{run["status"]} | '
                    f'{run["objective"]}'
                )

        continue
```

- [ ] **Step 3: Keep storage errors from terminating the program**

Change the workflow-entry exception handler in `main.py` from:

```python
    except ValueError as error:
```

to:

```python
    except (ValueError, RuntimeError) as error:
```

The existing print and `continue` remain unchanged, so storage failure displays `工作流已执行，但历史保存失败。` and returns to the prompt.

- [ ] **Step 4: Add the source module to project verification**

In `verify_project.py`, add this entry to `SOURCE_FILE_NAMES` after `workflow_entry.py`:

```python
    "workflow_history.py",
```

- [ ] **Step 5: Run syntax and focused regression checks**

Run:

```powershell
python -m py_compile main.py workflow_entry.py workflow_history.py
python test_workflow_history.py
python test_workflow_entry.py
```

Expected: compilation is silent and both tests print their pass messages.

- [ ] **Step 6: Run the complete checkpoint verification**

Run:

```powershell
python checkpoint_project.py
```

Expected:

```text
[PASS] compile workflow_history.py
[PASS] test_workflow_history.py
Summary: 39/39 tests passed.
Checkpoint created: ...
```

- [ ] **Step 7: Perform one manual command check**

Run:

```powershell
python main.py
```

Enter:

```text
查看项目记录
exit
```

Expected: the program prints `最近客户项目记录：`, shows `暂无项目记录` or recent rows, and exits normally.

- [ ] **Step 8: Record Day043 completion**

Append to `PROGRESS.md`:

```markdown
## Day043 — Complete

- Added SQLite-backed client workflow history.
- Persisted completed and failed workflow steps atomically.
- Blocked sensitive workflow input and generated output from storage.
- Added the `查看项目记录` command for recent summaries.
- Verification: `python checkpoint_project.py` — 39/39 tests passed.
```

- [ ] **Step 9: Commit the verified Day043 integration**

```powershell
git add main.py verify_project.py PROGRESS.md
git commit -m "feat: expose client workflow history"
```

- [ ] **Step 10: Confirm final repository state**

Run:

```powershell
git status --short
git log -4 --oneline
```

Expected: the working tree is clean and the three Day043 implementation commits appear above design commit `7cb6f00`.
