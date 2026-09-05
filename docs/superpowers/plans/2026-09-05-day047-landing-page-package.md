# Day047 Landing Page Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the Coding Agent response as a fixed three-file landing-page package and expose it through workflow results and history.

**Architecture:** A focused standard-library parser converts the Coding Agent JSON string into `LandingPagePackage`. The existing workflow validates immediately after Coding, keeps the raw JSON for downstream Agents, and attaches the parsed package to `WorkflowResult`. History reconstructs the package from the already-stored Coding step, avoiding a database migration.

**Tech Stack:** Python 3.13, `dataclasses`, `json`, existing Agents SDK and SQLite workflow history.

**Spec:** `docs/superpowers/specs/2026-09-05-day047-landing-page-package-design.md`

## Global Constraints

- The Coding Agent JSON must contain exactly `index.html`, `styles.css`, and `script.js`.
- HTML and CSS must be non-empty strings; JavaScript may be an empty string.
- Invalid Coding output must fail the Coding step and skip QA and Client Project Manager.
- Keep Client Project Manager text as `final_output` and expose the package separately as `landing_page`.
- Do not write generated files, execute generated code, change the database schema, add endpoints, or add dependencies.

---

### Task 1: Landing Page Package Contract and Parser

**Files:**
- Create: `landing_page_package.py`
- Create: `test_landing_page_package.py`
- Modify: `verify_project.py:7-29`

**Interfaces:**
- Consumes: Coding Agent raw output as `str`.
- Produces: `LandingPagePackage(files: dict[str, str])` and `parse_landing_page_package(raw_output: str) -> LandingPagePackage`.

- [ ] **Step 1: Write the failing parser test**

Create `test_landing_page_package.py`:

```python
import importlib.util
import json


module_spec = importlib.util.find_spec("landing_page_package")
assert module_spec is not None, "landing_page_package.py 尚未实现"

from landing_page_package import (
    LandingPagePackage,
    parse_landing_page_package,
)


files = {
    "index.html": "<main>Hello</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
package = parse_landing_page_package(
    json.dumps(files)
)

assert isinstance(package, LandingPagePackage)
assert package.files == files

invalid_outputs = (
    42,
    "not json",
    "[]",
    json.dumps({
        "index.html": "<main>Hello</main>",
        "styles.css": "main {}",
    }),
    json.dumps({
        **files,
        "README.md": "extra",
    }),
    json.dumps({
        **files,
        "script.js": 42,
    }),
    json.dumps({
        **files,
        "index.html": " ",
    }),
    json.dumps({
        **files,
        "styles.css": " ",
    }),
)

for raw_output in invalid_outputs:
    try:
        parse_landing_page_package(raw_output)
    except ValueError:
        pass
    else:
        raise AssertionError(
            f"无效 Coding 输出必须被拒绝：{raw_output}"
        )

print("Landing-page-package tests passed.")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe test_landing_page_package.py
```

Expected: FAIL because `landing_page_package.py` does not exist.

- [ ] **Step 3: Implement the minimal contract and parser**

Create `landing_page_package.py`:

```python
import json
from dataclasses import dataclass


REQUIRED_FILES = (
    "index.html",
    "styles.css",
    "script.js",
)


@dataclass
class LandingPagePackage:
    files: dict[str, str]


def parse_landing_page_package(raw_output):
    if not isinstance(raw_output, str):
        raise ValueError("Coding Agent 输出必须是字符串。")

    try:
        files = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "Coding Agent 必须返回有效 JSON。"
        ) from error

    if not isinstance(files, dict):
        raise ValueError("Coding Agent JSON 必须是对象。")

    if set(files) != set(REQUIRED_FILES):
        raise ValueError(
            "Coding Agent JSON 必须且只能包含 "
            "index.html、styles.css、script.js。"
        )

    if any(
        not isinstance(files[name], str)
        for name in REQUIRED_FILES
    ):
        raise ValueError("Landing Page 文件内容必须是字符串。")

    if not files["index.html"].strip():
        raise ValueError("index.html 不能为空。")

    if not files["styles.css"].strip():
        raise ValueError("styles.css 不能为空。")

    return LandingPagePackage(
        files={name: files[name] for name in REQUIRED_FILES}
    )
```

Add `"landing_page_package.py",` to `SOURCE_FILE_NAMES` in `verify_project.py`.

- [ ] **Step 4: Run the parser test and compilation**

Run:

```powershell
.\.venv\Scripts\python.exe test_landing_page_package.py
.\.venv\Scripts\python.exe -m py_compile landing_page_package.py verify_project.py
```

Expected: `Landing-page-package tests passed.` and no compilation output.

- [ ] **Step 5: Commit the parser**

```powershell
git add landing_page_package.py test_landing_page_package.py verify_project.py
git commit -m "feat: validate landing page packages"
```

---

### Task 2: Enforce the Contract in the Production Workflow

**Files:**
- Modify: `workflow_contract.py:1-13`
- Modify: `client_project_workflow.py:1-118`
- Modify: `main.py:134-144`
- Modify: `test_client_project_workflow.py:1-103`

**Interfaces:**
- Consumes: `parse_landing_page_package(raw_output: str) -> LandingPagePackage` from Task 1.
- Produces: `WorkflowResult.landing_page: LandingPagePackage | None` and fail-fast Coding validation.

- [ ] **Step 1: Update the workflow test with valid and invalid Coding output**

In `test_client_project_workflow.py`, import `json`, define a valid Coding result, and use it in the successful handlers:

```python
import json


coding_files = {
    "index.html": "<main>Hello</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
coding_output = json.dumps(coding_files)
```

Replace `handler("Coding 完成")` with `handler(coding_output)`. Replace the QA context assertion with:

```python
assert f"Coding 输出：\n{coding_output}" in (
    received_tasks[5].context
)
assert result.landing_page.files == coding_files
```

Append the fail-fast case:

```python
def must_not_run(task):
    raise AssertionError(
        f"{task.assigned_agent} 不应在 Coding 验证失败后运行"
    )


invalid_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": handler("not json"),
        "QA Agent": must_not_run,
        "Client Project Manager Agent": must_not_run,
    },
)

assert invalid_result.status == "failed"
assert len(invalid_result.steps) == 5
assert invalid_result.steps[-1].agent_name == "Coding Agent"
assert invalid_result.steps[-1].status == "failed"
assert invalid_result.landing_page is None
assert "必须返回有效 JSON" in invalid_result.error
```

- [ ] **Step 2: Run the workflow test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe test_client_project_workflow.py
```

Expected: FAIL because `WorkflowResult` has no `landing_page` field and Coding output is not validated.

- [ ] **Step 3: Add the optional package to `WorkflowResult`**

Update `workflow_contract.py`:

```python
from dataclasses import dataclass

from landing_page_package import LandingPagePackage
from task_contract import AgentResult


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_type: str
    status: str
    steps: list[AgentResult]
    final_output: str
    error: str | None = None
    landing_page: LandingPagePackage | None = None
```

- [ ] **Step 4: Validate immediately after Coding**

In `client_project_workflow.py`, import the parser:

```python
from landing_page_package import parse_landing_page_package
```

Initialize `landing_page = None` before the pipeline loop. After the existing failed-step check and before assigning `outputs[output_name]`, add:

```python
        if output_name == "Coding":
            try:
                landing_page = parse_landing_page_package(
                    step.output
                )
            except ValueError as error:
                step.status = "failed"
                step.error = str(error)
                return _failed_workflow(
                    workflow_id,
                    steps,
                )
```

Pass the package in the completed result:

```python
        landing_page=landing_page,
```

- [ ] **Step 5: Constrain only Landing Page responses from the Coding Agent**

In `main.py`, replace the Coding Agent instructions with:

```python
    instructions=(
        "你是专用软件开发 Agent。"
        "根据任务目标和技术背景输出最小、可维护的实现。"
        "优先复用现有代码和标准库，避免不必要的依赖与抽象。"
        "只依据已提供的项目事实，不声称运行过未实际执行的代码。"
        "当任务要求制作 Landing Page 时，只返回一个 JSON 对象，"
        "必须且只能包含 index.html、styles.css、script.js 三个字符串字段。"
        "不要使用 Markdown 代码围栏或添加 JSON 以外的说明。"
    ),
```

- [ ] **Step 6: Run focused workflow verification**

Run:

```powershell
.\.venv\Scripts\python.exe test_client_project_workflow.py
.\.venv\Scripts\python.exe -m py_compile main.py workflow_contract.py client_project_workflow.py
```

Expected: `Client-project-workflow tests passed.` and no compilation output.

- [ ] **Step 7: Commit workflow enforcement**

```powershell
git add main.py workflow_contract.py client_project_workflow.py test_client_project_workflow.py
git commit -m "feat: enforce landing page package output"
```

---

### Task 3: Reconstruct and Expose the Package

**Files:**
- Modify: `workflow_history.py:1-137`
- Modify: `test_workflow_history.py:1-130`
- Modify: `test_web_app.py:1-184`

**Interfaces:**
- Consumes: stored Coding step dictionaries and `WorkflowResult.landing_page` from Task 2.
- Produces: detailed workflow history with `landing_page` as `dict | None`; POST responses expose the nested dataclass through existing `asdict(result)`.

- [ ] **Step 1: Add failing history and API assertions**

In `test_workflow_history.py`, import `json` and define:

```python
landing_page_files = {
    "index.html": "<main>Stored</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
```

Add this Coding step to the completed result before the project-manager step:

```python
AgentResult(
    "task-coding",
    "Coding Agent",
    "completed",
    json.dumps(landing_page_files),
),
```

Include `"Coding Agent"` in the stored Agent-name assertion and add:

```python
assert stored["landing_page"] == {
    "files": landing_page_files,
}
assert stored_failed["landing_page"] is None
```

In `test_web_app.py`, import `LandingPagePackage`, construct the stub workflow with:

```python
    landing_page=LandingPagePackage(
        files={
            "index.html": "<main>Web</main>",
            "styles.css": "main { color: black; }",
            "script.js": "",
        }
    ),
```

Add assertions after the POST and detail requests:

```python
assert created["landing_page"] == asdict(
    workflow.landing_page
)
assert detail["landing_page"] == asdict(
    workflow.landing_page
)
```

- [ ] **Step 2: Run the focused tests to verify history fails**

Run:

```powershell
.\.venv\Scripts\python.exe test_workflow_history.py
.\.venv\Scripts\python.exe test_web_app.py
```

Expected: history test FAIL because detailed history has no `landing_page`; Web API assertion already passes through existing dataclass serialization.

- [ ] **Step 3: Reconstruct the package without a database migration**

In `workflow_history.py`, import the parser:

```python
from landing_page_package import parse_landing_page_package
```

Add this helper before `get_workflow_run`:

```python
def _landing_page_from_steps(steps):
    for step in steps:
        if (
            step.get("agent_name") == "Coding Agent"
            and step.get("status") == "completed"
        ):
            try:
                package = parse_landing_page_package(
                    step.get("output", "")
                )
            except ValueError:
                return None

            return asdict(package)

    return None
```

Parse `steps_json` once in `get_workflow_run`:

```python
    steps = json.loads(row[5])
```

Then return both:

```python
        "steps": steps,
        "landing_page": _landing_page_from_steps(steps),
```

- [ ] **Step 4: Run focused history and Web API verification**

Run:

```powershell
.\.venv\Scripts\python.exe test_workflow_history.py
.\.venv\Scripts\python.exe test_web_app.py
```

Expected: `Workflow-history tests passed.` and `Web-app tests passed.`

- [ ] **Step 5: Commit history and API exposure**

```powershell
git add workflow_history.py test_workflow_history.py test_web_app.py
git commit -m "feat: expose landing page packages"
```

---

### Task 4: Full Verification and Completion Record

**Files:**
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: all Day047 implementation tasks.
- Produces: verified checkpoint and completion record.

- [ ] **Step 1: Run complete verification**

Run:

```powershell
.\.venv\Scripts\python.exe checkpoint_project.py
```

Expected:

```text
[PASS] compile landing_page_package.py
[PASS] test_landing_page_package.py
Summary: 42/42 tests passed.
Checkpoint created: ...
```

- [ ] **Step 2: Record Day047 completion**

Append to `PROGRESS.md`:

```markdown
## Day047 — Complete

- Added a strict three-file `LandingPagePackage` contract.
- Validated Coding Agent JSON before QA and stopped invalid workflows.
- Exposed packages through live workflow results and detailed history.
- Preserved the existing database schema and added no dependencies.
- Verification: `python checkpoint_project.py` — 42/42 tests passed.
```

- [ ] **Step 3: Commit the completion record**

```powershell
git add PROGRESS.md
git commit -m "docs: complete Day047 landing page package"
```
