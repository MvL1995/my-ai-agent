# Day046 Landing Page Production Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing client-project workflow into a seven-Agent landing-page production chain that returns a reviewable delivery package.

**Architecture:** Keep the existing router, executor, Agent registry, workflow contract, history, API, and Web UI. Change only the workflow sequence and its focused tests; each step receives the original context plus the upstream outputs it needs, and the workflow remains fail-fast.

**Tech Stack:** Python 3.13 standard library, OpenAI Agents SDK already installed, assert-based tests, SQLite workflow history.

**Spec:** `docs/superpowers/specs/2026-09-05-day046-landing-page-production-pipeline-design.md`

## Global Constraints

- Reuse the existing `TaskBrief`, router, executor, handler registry, workflow result, history persistence, API, and Web UI.
- Stop at the first failed Agent and preserve all completed steps plus the failed step.
- Return Agent outputs as a reviewable package; do not write generated website files or execute generated code.
- Add no dependency and no new runtime abstraction.

---

## File Map

- Modify `client_project_workflow.py`: define and execute the seven-step pipeline.
- Modify `test_client_project_workflow.py`: verify order, final output, and required context flow.
- Modify `test_client_project_workflow_failure.py`: verify fail-fast behavior in the expanded chain.
- Modify `PROGRESS.md`: record Day046 only after complete verification succeeds.

### Task 1: Expand and verify the client-project workflow

**Files:**
- Modify: `client_project_workflow.py`
- Test: `test_client_project_workflow.py`
- Test: `test_client_project_workflow_failure.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `route_task(task_type, objective, context)`, `execute_task(task, handlers)`.
- Produces: unchanged `run_client_project_workflow(objective, context, handlers) -> WorkflowResult`.

- [ ] **Step 1: Expand the successful workflow test**

Replace the handler map and expected Agent order in `test_client_project_workflow.py` with all seven Agents:

```python
result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": handler("Coding 完成"),
        "QA Agent": handler("QA 完成"),
        "Client Project Manager Agent": handler("项目计划完成"),
    },
)

assert [step.agent_name for step in result.steps] == [
    "Search Agent",
    "Strategy Agent",
    "Copywriting Agent",
    "Web Design Agent",
    "Coding Agent",
    "QA Agent",
    "Client Project Manager Agent",
]
assert result.final_output == "项目计划完成"
assert "Research 输出：\nResearch 完成" in received_tasks[2].context
assert "Strategy 输出：\nStrategy 完成" in received_tasks[2].context
assert "Copywriting 输出：\nCopywriting 完成" in received_tasks[3].context
assert "Web Design 输出：\nWeb Design 完成" in received_tasks[4].context
assert "Coding 输出：\nCoding 完成" in received_tasks[5].context
assert "QA 输出：\nQA 完成" in received_tasks[6].context
```

- [ ] **Step 2: Expand the failure test**

Change `test_client_project_workflow_failure.py` so Coding fails after the first four Agents and QA/project management must not run:

```python
def completed_handler(task):
    called_agents.append(task.assigned_agent)
    return f"{task.assigned_agent} 完成"


def coding_handler(task):
    called_agents.append(task.assigned_agent)
    raise RuntimeError("Coding 暂时不可用")


def forbidden_handler(task):
    raise AssertionError("Coding 失败后不得调用下游 Agent")


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": completed_handler,
        "Strategy Agent": completed_handler,
        "Copywriting Agent": completed_handler,
        "Web Design Agent": completed_handler,
        "Coding Agent": coding_handler,
        "QA Agent": forbidden_handler,
        "Client Project Manager Agent": forbidden_handler,
    },
)

assert result.status == "failed"
assert result.error == "Coding Agent: Coding 暂时不可用"
assert [step.status for step in result.steps] == [
    "completed", "completed", "completed", "completed", "failed"
]
assert called_agents == [
    "Search Agent",
    "Strategy Agent",
    "Copywriting Agent",
    "Web Design Agent",
    "Coding Agent",
]
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run:

```powershell
python test_client_project_workflow.py
python test_client_project_workflow_failure.py
```

Expected: at least one assertion fails because the current workflow runs only Research, Strategy, and Client Project Manager.

- [ ] **Step 4: Implement the minimal seven-step pipeline**

In `client_project_workflow.py`, keep `_run_step()` and `_failed_workflow()`, then add the pipeline and context builder:

```python
PIPELINE = (
    ("research", "Research", ()),
    ("strategy", "Strategy", ("Research",)),
    ("copywriting", "Copywriting", ("Research", "Strategy")),
    ("web_design", "Web Design", ("Strategy", "Copywriting")),
    ("coding", "Coding", ("Copywriting", "Web Design")),
    ("qa", "QA", ("Copywriting", "Web Design", "Coding")),
    (
        "client_management",
        "Client Project Manager",
        ("Research", "Strategy", "Copywriting", "Web Design", "Coding", "QA"),
    ),
)


def _build_step_context(context, outputs, dependencies):
    if not dependencies:
        return context

    blocks = [f"原始项目背景：\n{context}"]
    blocks.extend(
        f"{name} 输出：\n{outputs[name]}"
        for name in dependencies
    )
    return "\n\n".join(blocks)
```

Replace the body of `run_client_project_workflow()` after the ID is created:

```python
    steps = []
    outputs = {}

    for task_type, output_name, dependencies in PIPELINE:
        step = _run_step(
            task_type,
            objective,
            _build_step_context(context, outputs, dependencies),
            handlers,
        )
        steps.append(step)

        if step.status == "failed":
            return _failed_workflow(workflow_id, steps)

        outputs[output_name] = step.output

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=steps,
        final_output=steps[-1].output,
    )
```

- [ ] **Step 5: Run focused tests and compile checks**

Run:

```powershell
python test_client_project_workflow.py
python test_client_project_workflow_failure.py
python -m py_compile client_project_workflow.py
```

Expected: both tests print their passing messages and compilation exits with code `0`.

- [ ] **Step 6: Run full verification and create a checkpoint**

Run:

```powershell
python checkpoint_project.py
```

Expected: every source file compiles, every discovered test passes, and a new checkpoint path is printed.

- [ ] **Step 7: Record completion and commit**

Append to `PROGRESS.md`:

```markdown
## Day046 — Complete

- Expanded the client-project workflow to Research, Strategy, Copywriting, Web Design, Coding, QA, and Client Project Manager.
- Preserved focused upstream context and fail-fast behavior.
- Reused the existing task, execution, history, API, and Web UI infrastructure.
- Verification: `python checkpoint_project.py` — all tests passed.
```

Then run:

```powershell
git add client_project_workflow.py test_client_project_workflow.py test_client_project_workflow_failure.py PROGRESS.md docs/superpowers/plans/2026-09-05-day046-landing-page-production-pipeline.md
git commit -m "feat: add landing page production pipeline"
```

