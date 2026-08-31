# Day028 Task Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute a `TaskBrief` through its registered specialist handler and return an `AgentResult`.

**Architecture:** Add one small `task_executor.py` module. A plain handler registry maps Agent names to callables, avoiding Agents SDK coupling while preserving the shared task/result contracts.

**Tech Stack:** Python standard library and existing project dataclasses.

---

## Task 1: Lock the executor contract with a failing test

**Files:**
- Create: `test_task_executor.py`

- [x] Add a test that passes the original task to the selected handler.
- [x] Assert the exact completed `AgentResult` fields.
- [x] Assert handler exceptions become failed `AgentResult` values.
- [x] Assert an unregistered Agent raises `ValueError`.
- [x] Run `python test_task_executor.py` and confirm it fails because `task_executor.py` is absent.

## Task 2: Build the minimal executor

**Files:**
- Create: `task_executor.py`

- [x] Look up the handler with `task.assigned_agent`.
- [x] Reject missing registrations with `ValueError`.
- [x] Execute the handler and return a completed result.
- [x] Convert specialist exceptions into failed results.
- [x] Run `python test_task_executor.py` and confirm it passes.

## Task 3: Integrate verification and record completion

**Files:**
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

- [x] Add `task_executor.py` to `SOURCE_FILE_NAMES`.
- [x] Record Day028 completion in `PROGRESS.md`.
- [x] Run `python checkpoint_project.py` and confirm 21/21 tests pass.
- [x] Commit only the Day028 files.
