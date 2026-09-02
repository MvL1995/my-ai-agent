# Day041 Client Project Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one explicit client-project command through Research, Strategy, and Client Project Manager agents and return one structured workflow result.

**Architecture:** Add a small `WorkflowResult` contract and one fixed sequential workflow that reuses the existing task router, task executor, agent handlers, `TaskBrief`, and `AgentResult`. A separate entry parser handles only the explicit `client_project` command, and `main.py` checks it before the existing single-task path.

**Tech Stack:** Python 3 standard library, existing OpenAI Agents SDK integration, existing assert-based test scripts.

**Spec:** `docs/superpowers/specs/2026-09-02-client-project-workflow-design.md`

## Global Constraints

- Keep Ponytail full: no workflow framework, DAG engine, persistence, queue, retry layer, or new dependency.
- Reuse `route_task()`, `execute_task()`, and the existing `task_handlers` mapping.
- Accept only `工作流：client_project | 目标 | 项目背景`.
- Run steps sequentially and stop after the first failed `AgentResult`.
- Preserve every attempted step result in order.
- Do not call external APIs from tests.
- Do not modify memory behavior, search retry behavior, or existing single-task behavior.

---

## Task 1: Add the workflow contract and successful three-step execution

**Files:**

- Create: `workflow_contract.py`
- Create: `client_project_workflow.py`
- Create: `test_client_project_workflow.py`

- [ ] **Step 1: Write the failing success-path test**

Create `test_client_project_workflow.py`:

```python
import importlib.util


contract_spec = importlib.util.find_spec("workflow_contract")
workflow_spec = importlib.util.find_spec(
    "client_project_workflow"
)

assert contract_spec is not None, (
    "workflow_contract.py 尚未实现"
)
assert workflow_spec is not None, (
    "client_project_workflow.py 尚未实现"
)

from client_project_workflow import (
    run_client_project_workflow,
)
from workflow_contract import WorkflowResult


received_tasks = []


def handler(output):
    def run(task):
        received_tasks.append(task)
        return output

    return run


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Client Project Manager Agent": handler(
            "项目计划完成"
        ),
    },
)

assert isinstance(result, WorkflowResult)
assert result.workflow_id.startswith("workflow-")
assert result.workflow_type == "client_project"
assert result.status == "completed"
assert result.final_output == "项目计划完成"
assert result.error is None
assert [step.agent_name for step in result.steps] == [
    "Search Agent",
    "Strategy Agent",
    "Client Project Manager Agent",
]

assert received_tasks[0].task_type == "research"
assert received_tasks[0].context == (
    "客户经营吉隆坡本地餐厅"
)

assert received_tasks[1].task_type == "strategy"
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[1].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[1].context
)

assert received_tasks[2].task_type == (
    "client_management"
)
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[2].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[2].context
)
assert "Strategy 输出：\nStrategy 完成" in (
    received_tasks[2].context
)

print("Client-project-workflow tests passed.")
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python test_client_project_workflow.py
```

Expected: fail with `workflow_contract.py 尚未实现`.

- [ ] **Step 3: Add the workflow result contract**

Create `workflow_contract.py`:

```python
from dataclasses import dataclass

from task_contract import AgentResult


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_type: str
    status: str
    steps: list[AgentResult]
    final_output: str
    error: str | None = None
```

- [ ] **Step 4: Add the minimum successful workflow**

Create `client_project_workflow.py`:

```python
from uuid import uuid4

from task_executor import execute_task
from task_router import route_task
from workflow_contract import WorkflowResult


def _run_step(
    task_type,
    objective,
    context,
    handlers,
):
    task = route_task(
        task_type,
        objective,
        context,
    )
    return execute_task(task, handlers)


def run_client_project_workflow(
    objective,
    context,
    handlers,
):
    workflow_id = f"workflow-{uuid4().hex}"

    research = _run_step(
        "research",
        objective,
        context,
        handlers,
    )
    strategy_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}"
    )
    strategy = _run_step(
        "strategy",
        objective,
        strategy_context,
        handlers,
    )
    project_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}\n\n"
        f"Strategy 输出：\n{strategy.output}"
    )
    project = _run_step(
        "client_management",
        objective,
        project_context,
        handlers,
    )

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=[research, strategy, project],
        final_output=project.output,
    )
```

- [ ] **Step 5: Run the test to verify GREEN**

Run:

```powershell
python test_client_project_workflow.py
```

Expected: `Client-project-workflow tests passed.`

- [ ] **Step 6: Commit Task 1**

```powershell
git add workflow_contract.py client_project_workflow.py test_client_project_workflow.py
git commit -m "feat: add client project workflow"
```

---

## Task 2: Stop the workflow after the first failed step

**Files:**

- Create: `test_client_project_workflow_failure.py`
- Modify: `client_project_workflow.py`

- [ ] **Step 1: Write the failing fail-fast test**

Create `test_client_project_workflow_failure.py`:

```python
from client_project_workflow import (
    run_client_project_workflow,
)


called_agents = []


def research_handler(task):
    called_agents.append(task.assigned_agent)
    return "Research 完成"


def strategy_handler(task):
    called_agents.append(task.assigned_agent)
    raise RuntimeError("Strategy 暂时不可用")


def forbidden_project_handler(task):
    raise AssertionError(
        "Strategy 失败后不得调用项目管理 Agent"
    )


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": research_handler,
        "Strategy Agent": strategy_handler,
        "Client Project Manager Agent": (
            forbidden_project_handler
        ),
    },
)

assert result.status == "failed"
assert result.final_output == ""
assert result.error == (
    "Strategy Agent: Strategy 暂时不可用"
)
assert [step.status for step in result.steps] == [
    "completed",
    "failed",
]
assert called_agents == [
    "Search Agent",
    "Strategy Agent",
]

print("Client-project-workflow failure tests passed.")
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python test_client_project_workflow_failure.py
```

Expected: fail because the current workflow calls the project manager after Strategy fails.

- [ ] **Step 3: Add one shared failure result helper and three guards**

Add this helper below `_run_step()` in `client_project_workflow.py`:

```python
def _failed_workflow(workflow_id, steps):
    failed_step = steps[-1]
    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="failed",
        steps=steps,
        final_output="",
        error=(
            f"{failed_step.agent_name}: "
            f"{failed_step.error}"
        ),
    )
```

Replace the body of `run_client_project_workflow()` after `workflow_id` with:

```python
    research = _run_step(
        "research",
        objective,
        context,
        handlers,
    )
    steps = [research]

    if research.status == "failed":
        return _failed_workflow(workflow_id, steps)

    strategy_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}"
    )
    strategy = _run_step(
        "strategy",
        objective,
        strategy_context,
        handlers,
    )
    steps.append(strategy)

    if strategy.status == "failed":
        return _failed_workflow(workflow_id, steps)

    project_context = (
        f"原始项目背景：\n{context}\n\n"
        f"Research 输出：\n{research.output}\n\n"
        f"Strategy 输出：\n{strategy.output}"
    )
    project = _run_step(
        "client_management",
        objective,
        project_context,
        handlers,
    )
    steps.append(project)

    if project.status == "failed":
        return _failed_workflow(workflow_id, steps)

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=steps,
        final_output=project.output,
    )
```

- [ ] **Step 4: Run both workflow tests to verify GREEN**

Run:

```powershell
python test_client_project_workflow.py
python test_client_project_workflow_failure.py
```

Expected: both tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add client_project_workflow.py test_client_project_workflow_failure.py
git commit -m "test: enforce client workflow fail fast"
```

---

## Task 3: Add the explicit workflow command entry

**Files:**

- Create: `workflow_entry.py`
- Create: `test_workflow_entry.py`

- [ ] **Step 1: Write the failing parser and dispatch test**

Create `test_workflow_entry.py`:

```python
import importlib.util


module_spec = importlib.util.find_spec("workflow_entry")
assert module_spec is not None, "workflow_entry.py 尚未实现"

from workflow_contract import WorkflowResult
from workflow_entry import (
    WORKFLOW_COMMAND_USAGE,
    execute_workflow_request,
    extract_workflow_request,
)


assert extract_workflow_request("你好") is None
assert extract_workflow_request(
    "工作流： client_project | 启动客户项目 | 餐厅客户 "
) == (
    "client_project",
    "启动客户项目",
    "餐厅客户",
)

received = {}


def fake_workflow(objective, context, handlers):
    received["objective"] = objective
    received["context"] = context
    received["handlers"] = handlers
    return WorkflowResult(
        workflow_id="workflow-test",
        workflow_type="client_project",
        status="completed",
        steps=[],
        final_output="客户项目计划",
    )


handlers = {"Search Agent": object()}
result = execute_workflow_request(
    "工作流：client_project | 启动客户项目 | 餐厅客户",
    handlers,
    run_workflow=fake_workflow,
)

assert result.final_output == "客户项目计划"
assert received == {
    "objective": "启动客户项目",
    "context": "餐厅客户",
    "handlers": handlers,
}

for invalid_input in (
    "工作流：",
    "工作流：client_project | 启动客户项目",
    "工作流：client_project | | 餐厅客户",
):
    try:
        extract_workflow_request(invalid_input)
    except ValueError as error:
        assert str(error) == WORKFLOW_COMMAND_USAGE
    else:
        raise AssertionError(
            "无效工作流命令必须触发 ValueError"
        )

try:
    extract_workflow_request(
        "工作流：unknown | 启动客户项目 | 餐厅客户"
    )
except ValueError as error:
    assert str(error) == (
        "Unsupported workflow type: unknown"
    )
else:
    raise AssertionError(
        "未知工作流类型必须触发 ValueError"
    )

print("Workflow-entry tests passed.")
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python test_workflow_entry.py
```

Expected: fail with `workflow_entry.py 尚未实现`.

- [ ] **Step 3: Implement the narrow parser and dispatcher**

Create `workflow_entry.py`:

```python
from client_project_workflow import (
    run_client_project_workflow,
)


WORKFLOW_COMMAND_PREFIX = "工作流："
WORKFLOW_COMMAND_USAGE = (
    "工作流格式：工作流：client_project | 目标 | 项目背景"
)


def extract_workflow_request(user_input):
    if not user_input.startswith(
        WORKFLOW_COMMAND_PREFIX
    ):
        return None

    content = user_input[
        len(WORKFLOW_COMMAND_PREFIX):
    ]
    fields = [
        field.strip()
        for field in content.split("|", 2)
    ]

    if len(fields) != 3 or not all(fields):
        raise ValueError(WORKFLOW_COMMAND_USAGE)

    workflow_type, objective, context = fields
    workflow_type = workflow_type.lower()

    if workflow_type != "client_project":
        raise ValueError(
            "Unsupported workflow type: "
            f"{workflow_type}"
        )

    return workflow_type, objective, context


def execute_workflow_request(
    user_input,
    handlers,
    run_workflow=run_client_project_workflow,
):
    request = extract_workflow_request(user_input)

    if request is None:
        return None

    _, objective, context = request
    return run_workflow(objective, context, handlers)
```

- [ ] **Step 4: Run the entry test to verify GREEN**

Run:

```powershell
python test_workflow_entry.py
```

Expected: `Workflow-entry tests passed.`

- [ ] **Step 5: Commit Task 3**

```powershell
git add workflow_entry.py test_workflow_entry.py
git commit -m "feat: add client workflow command"
```

---

## Task 4: Wire the workflow command into Main Agent

**Files:**

- Create: `test_main_workflow_entry.py`
- Modify: `main.py`
- Modify: `verify_project.py`

- [ ] **Step 1: Write the failing Main wiring test**

Create `test_main_workflow_entry.py`:

```python
import builtins
import os
import runpy
import tempfile
from pathlib import Path

import agent_registry
import agents
import memory
import task_entry
import workflow_entry
from workflow_contract import WorkflowResult


project_directory = Path(__file__).resolve().parent
original_input = builtins.input
original_db_path = memory.DB_PATH
original_build_handlers = (
    agent_registry.build_agent_handlers
)
original_execute_task = task_entry.execute_task_request
original_execute_workflow = (
    workflow_entry.execute_workflow_request
)
original_run_sync = agents.Runner.run_sync
original_working_directory = Path.cwd()
captured = {}


def fake_build_handlers(*args, **kwargs):
    handlers = {"Search Agent": object()}
    captured["handlers"] = handlers
    return handlers


def fake_execute_workflow(user_input, handlers):
    captured["user_input"] = user_input
    captured["received_handlers"] = handlers
    return WorkflowResult(
        workflow_id="workflow-test",
        workflow_type="client_project",
        status="completed",
        steps=[],
        final_output="客户项目计划已生成",
    )


def forbidden_path(*args, **kwargs):
    raise AssertionError(
        "工作流命令不得进入单任务或普通对话路径"
    )


with tempfile.TemporaryDirectory(
    ignore_cleanup_errors=True
) as temp_dir:
    try:
        os.chdir(temp_dir)
        memory.DB_PATH = str(
            Path(temp_dir) / "test_memory.db"
        )
        agent_registry.build_agent_handlers = (
            fake_build_handlers
        )
        workflow_entry.execute_workflow_request = (
            fake_execute_workflow
        )
        task_entry.execute_task_request = forbidden_path
        agents.Runner.run_sync = staticmethod(
            forbidden_path
        )

        command = (
            "工作流：client_project | 启动客户项目 | "
            "餐厅客户"
        )
        user_inputs = iter([command, "exit"])
        builtins.input = lambda prompt="": next(
            user_inputs
        )

        runpy.run_path(
            str(project_directory / "main.py"),
            run_name="day041_main_test",
        )

        assert captured["user_input"] == command
        assert captured["received_handlers"] is (
            captured["handlers"]
        )
    finally:
        builtins.input = original_input
        memory.DB_PATH = original_db_path
        agent_registry.build_agent_handlers = (
            original_build_handlers
        )
        task_entry.execute_task_request = (
            original_execute_task
        )
        workflow_entry.execute_workflow_request = (
            original_execute_workflow
        )
        agents.Runner.run_sync = original_run_sync
        os.chdir(original_working_directory)

print("Main-workflow-entry tests passed.")
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
python test_main_workflow_entry.py
```

Expected: fail because `main.py` does not call `execute_workflow_request()` and reaches the forbidden single-task path.

- [ ] **Step 3: Import the workflow entry in `main.py`**

Add below the `task_entry` import:

```python
from workflow_entry import execute_workflow_request
```

- [ ] **Step 4: Handle workflow commands before single-task commands**

In `main.py`, insert this block immediately before the existing `try:` that calls `execute_task_request()`:

```python
    try:
        workflow_result = execute_workflow_request(
            user_input,
            task_handlers,
        )
    except ValueError as error:
        print(f"Main Agent: {error}")
        continue

    if workflow_result is not None:
        if workflow_result.status == "completed":
            speaker = "Client Project Workflow"
            message = workflow_result.final_output
        else:
            speaker = "Main Agent"
            message = workflow_result.error

        print(f"\n{speaker}:", message)
        continue
```

- [ ] **Step 5: Register the three new source files for compilation**

Add these entries to `SOURCE_FILE_NAMES` in `verify_project.py`:

```python
    "workflow_contract.py",
    "client_project_workflow.py",
    "workflow_entry.py",
```

- [ ] **Step 6: Run the wiring test to verify GREEN**

Run:

```powershell
python test_main_workflow_entry.py
```

Expected: `Main-workflow-entry tests passed.`

- [ ] **Step 7: Run focused regression tests**

Run:

```powershell
python test_main_task_entry.py
python test_task_entry.py
python test_task_pipeline.py
python test_task_executor.py
```

Expected: all four existing task-path tests pass.

- [ ] **Step 8: Commit Task 4**

```powershell
git add main.py verify_project.py test_main_workflow_entry.py
git commit -m "feat: wire client workflow into main"
```

---

## Task 5: Verify, record, and checkpoint Day041

**Files:**

- Modify: `PROGRESS.md`

- [ ] **Step 1: Run complete project verification**

Run:

```powershell
python verify_project.py
```

Expected:

```text
Summary: 38/38 tests passed.
```

- [ ] **Step 2: Scan for accidental placeholders**

Run:

```powershell
rg -n "TODO|FIXME|pass$|NotImplemented" workflow_contract.py client_project_workflow.py workflow_entry.py test_client_project_workflow.py test_client_project_workflow_failure.py test_workflow_entry.py test_main_workflow_entry.py
```

Expected: no output.

- [ ] **Step 3: Confirm contract type consistency**

Verify:

- `WorkflowResult.steps` is `list[AgentResult]`.
- Every attempted step appends one existing `AgentResult` unchanged.
- Completed workflows use the Client Project Manager output.
- Failed workflows use empty `final_output` and one non-empty `error`.

- [ ] **Step 4: Record Day041 completion**

Append to `PROGRESS.md`:

```markdown

## Day041 — Complete

- Added a fixed Research → Strategy → Client Project Manager workflow.
- Added structured `WorkflowResult` output and fail-fast execution.
- Added the explicit `工作流：client_project | 目标 | 项目背景` entry.
- Added successful, failed, parser, and Main wiring tests.
- Verification: `python verify_project.py` — 38/38 tests passed.
```

- [ ] **Step 5: Run checkpoint verification**

Run:

```powershell
python checkpoint_project.py
```

Expected:

```text
Summary: 38/38 tests passed.
Checkpoint created:
```

The second line may include the generated checkpoint directory after the colon.

- [ ] **Step 6: Commit completion record**

```powershell
git add PROGRESS.md
git commit -m "docs: complete Day041 client workflow"
```

- [ ] **Step 7: Review the final diff and history**

Run:

```powershell
git status --short
git log --oneline -5
```

Expected: clean worktree and the Day041 commits visible.
