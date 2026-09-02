# Day043 Workflow History Design

## Goal

Persist every client-project workflow run so completed and failed runs can be
reviewed after the process exits.

## Scope

Day043 adds local workflow-history storage and a minimal recent-history command.
It does not add search filters, editing, deletion, replay, a Web UI, encryption,
or a new database dependency.

## Existing Flow

`workflow_entry.execute_workflow_request()` parses the request and calls
`run_client_project_workflow()`. The workflow returns one `WorkflowResult`
containing its ID, status, attempted agent steps, final output, and error. The
result is currently printed and then lost.

## Architecture

Add `workflow_history.py` as the single persistence boundary. It reuses
`long_term_memory.db` and the standard-library `sqlite3`, `json`, and
`dataclasses` modules. Workflow history uses its own table and does not change
the existing memory tables or `WorkflowResult`.

`workflow_entry.execute_workflow_request()` remains the orchestration boundary:
it validates the parsed input, runs the workflow, saves exactly one record, and
returns the original result.

## Database Schema

Create `workflow_runs` with these columns:

```sql
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
```

`steps_json` stores the ordered `AgentResult` values as JSON. A single insert
persists the complete run atomically. The primary key prevents duplicate
workflow IDs.

## Public API

`workflow_history.py` exposes:

- `init_workflow_history_db()` — creates `workflow_runs` when missing.
- `save_workflow_run(objective, context, result)` — serializes and inserts one
  complete `WorkflowResult`.
- `get_workflow_history(limit=10)` — returns newest-first summary dictionaries
  containing creation time, workflow ID, type, status, and objective.
- `get_workflow_run(workflow_id)` — returns one full dictionary with decoded
  ordered steps, or `None` when the ID does not exist.

The query functions reject non-positive limits and blank workflow IDs with
`ValueError`.

## Data Flow

1. Parse `客户项目：目标 | 项目背景` or the existing explicit workflow form.
2. Check the objective and context with the existing
   `contains_sensitive_memory()` guard.
3. Reject sensitive input before any specialist agent runs.
4. Run Research, Strategy, and Client Project Management with the existing
   fail-fast workflow.
5. Before insertion, check persisted step outputs, final output, and error with
   the same sensitive-data guard.
6. Insert one record for either a completed or failed workflow.
7. Return the unchanged `WorkflowResult` only after the insert succeeds.

## User Command

Add one exact command to `main.py`:

```text
查看项目记录
```

It prints the latest ten summaries: creation time, workflow ID, status, and
objective. Day043 does not add a full-detail command because the full record is
already available through `get_workflow_run()` for later UI work.

## Error Handling

- Unsupported or malformed workflow requests keep their existing `ValueError`
  behavior.
- Sensitive input raises `ValueError` and neither executes nor saves a run.
- Sensitive generated output raises `ValueError` and is not written to history.
- Duplicate workflow IDs surface as a storage error; no second row is created.
- SQLite or serialization failures are reported by `main.py` as
  `工作流已执行，但历史保存失败。` The program continues and never claims the
  run was saved.
- Failed agent workflows are valid history records and retain all attempted
  steps plus the workflow error.

## Testing

Add one focused `test_workflow_history.py` using a temporary SQLite database.
It verifies:

- a completed workflow stores objective, context, all three ordered steps, and
  final output;
- a failed workflow stores attempted steps and its error;
- sensitive objective or context prevents execution and insertion;
- sensitive generated output prevents insertion;
- duplicate workflow IDs do not create a second row;
- recent-history ordering and limits;
- full-record lookup and missing-ID behavior;
- `execute_workflow_request()` saves exactly once and returns the original
  result.

Add `workflow_history.py` to `verify_project.py`, then run
`python checkpoint_project.py`. Acceptance is **39/39 tests passed** with a new
checkpoint and no regression in existing commands.
