# Day030 Task Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combine task routing and task execution behind one stable function.

**Architecture:** Add one orchestration function that delegates to existing components and returns their `AgentResult` unchanged.

**Tech Stack:** Python standard library and existing project modules.

---

## Task 1: Lock the pipeline contract

**Files:**
- Create: `test_task_pipeline.py`

- [x] Route and execute a research task through one call.
- [x] Confirm the handler receives the routed `TaskBrief`.
- [x] Confirm specialist failure returns a failed result.
- [x] Confirm unsupported task types and missing handlers raise `ValueError`.
- [x] Run the test and confirm it fails because `task_pipeline.py` is absent.

## Task 2: Build the minimal pipeline

**Files:**
- Create: `task_pipeline.py`

- [x] Route inputs with `route_task()`.
- [x] Execute the resulting task with `execute_task()`.
- [x] Return the `AgentResult` unchanged.
- [x] Run the focused test and confirm it passes.

## Task 3: Verify and record Day030

**Files:**
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

- [x] Add `task_pipeline.py` to source verification.
- [x] Record Day030 completion.
- [x] Run `python checkpoint_project.py` and confirm 23/23 tests pass.
- [x] Commit only Day030 files.
