# Day029 Agent Handler Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register the existing Search Agent as a Task Executor handler.

**Architecture:** Add one registry factory that adapts `TaskBrief` to the existing `execute_search()` API. Keep the interactive `main.py` loop unchanged.

**Tech Stack:** Python standard library and existing project modules.

---

## Task 1: Lock the registry contract

**Files:**
- Create: `test_agent_registry.py`

- [x] Assert `Search Agent` is registered.
- [x] Execute a routed research task through `execute_task()`.
- [x] Confirm objective and context reach the search request.
- [x] Confirm failed search becomes a failed `AgentResult`.
- [x] Run the test and confirm it fails because `agent_registry.py` is absent.

## Task 2: Build the minimal registry

**Files:**
- Create: `agent_registry.py`

- [x] Build a Search Agent task handler.
- [x] Reuse `execute_search()` and its optional cache/run function.
- [x] Return completed search text.
- [x] Raise `RuntimeError` for non-completed search outcomes.
- [x] Run the focused test and confirm it passes.

## Task 3: Verify and record Day029

**Files:**
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

- [x] Add `agent_registry.py` to source verification.
- [x] Record Day029 completion.
- [x] Run `python checkpoint_project.py` and confirm 22/22 tests pass.
- [x] Commit only Day029 files.
