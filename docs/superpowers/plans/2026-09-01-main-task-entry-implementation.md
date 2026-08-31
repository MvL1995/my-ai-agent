# Day031 Main Agent Task Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a controlled task command to the Main Agent interactive loop.

**Architecture:** Parse explicit commands in a small testable boundary module, then reuse the existing registry and pipeline from `main.py`.

**Tech Stack:** Python standard library and existing project modules.

---

## Task 1: Lock the task-entry contract

**Files:**
- Create: `test_task_entry.py`

- [x] Confirm non-task input returns `None`.
- [x] Confirm valid input is trimmed and executed through the pipeline.
- [x] Confirm malformed commands raise a usage `ValueError`.
- [x] Run the test and confirm it fails because `task_entry.py` is absent.

## Task 2: Build the entry boundary

**Files:**
- Create: `task_entry.py`

- [x] Parse `任务：task_type | objective | context`.
- [x] Return `None` for ordinary messages.
- [x] Delegate valid requests to `run_task_pipeline()`.
- [x] Run the focused test and confirm it passes.

## Task 3: Wire Main Agent safely

**Files:**
- Modify: `main.py`
- Create: `test_main_task_entry.py`

- [x] Build the shared handler registry once.
- [x] Execute explicit task commands before ordinary Main Agent chat.
- [x] Print completed and failed results with the correct speaker.
- [x] Confirm existing search-cache wiring remains intact.
- [x] Run both Day031 tests and confirm they pass.

## Task 4: Verify and record Day031

**Files:**
- Modify: `verify_project.py`
- Modify: `PROGRESS.md`

- [x] Add `task_entry.py` to source verification.
- [x] Record Day031 completion.
- [x] Run `python checkpoint_project.py` and confirm 25/25 tests pass.
- [x] Commit only Day031 files.
