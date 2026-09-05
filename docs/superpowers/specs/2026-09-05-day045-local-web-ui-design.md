# Day045 Local Web UI Design

## Goal

Add a local browser-based operator console for submitting client projects to the existing AI Agency workflow and reviewing saved results.

## Scope

Day045 includes:

- A structured form with required `objective` and `context` fields.
- Synchronous execution of the existing Research → Strategy → Client Project Manager workflow.
- Display of workflow status, final output, and individual Agent steps.
- A list of recent workflow runs and a detail view for one run.
- Local-only operation on `127.0.0.1`.

Day045 excludes chat, streaming output, authentication, public deployment, background queues, billing, and external client access.

## Architecture

The browser sends JSON requests to a small Python standard-library HTTP server in `web_app.py`. The server reuses `execute_workflow_request()`, `get_workflow_history()`, and `get_workflow_run()`; it does not duplicate Agent or database logic.

`main.py` will expose its existing Agent setup without starting the terminal loop when imported. The terminal loop remains available through a guarded `run_cli()` entry point.

The frontend lives in `web/index.html`. HTML, CSS, and JavaScript remain in that single file for this local MVP.

## Endpoints

- `GET /` returns the operator console.
- `POST /api/workflows` validates `objective` and `context`, runs the existing client workflow, and returns its stored result.
- `GET /api/workflows` returns recent workflow summaries.
- `GET /api/workflows/{workflow_id}` returns one stored workflow with its Agent steps.

## Interface

The page has four areas:

1. Header with product name and local status.
2. Client brief form with objective, context, and submit button.
3. Execution panel showing loading, failure, or completed output and Agent steps.
4. Recent projects list with selectable detail records.

The submit button is disabled during execution and restored after completion or failure.

## Validation and Errors

- Missing or blank fields return HTTP `400` with a specific message.
- Existing sensitive-content checks remain authoritative.
- Unknown workflow IDs return HTTP `404`.
- Expected workflow failures return a structured error response and remain visible for retry.
- Unexpected server errors return a generic HTTP `500` message without exposing tracebacks to the browser.
- Tests use stub workflow functions and must not call the OpenAI API.

## Verification

- Add one focused Web UI test file covering page delivery, valid submission, validation failure, history, detail, and missing records.
- Keep all existing terminal and workflow tests passing.
- Manually confirm the local page can submit a project and reopen its saved detail.
- Run the existing project verification once at completion.

## Completion Criteria

Day045 is complete when a local user can submit a client project in the browser, receive the three-Agent workflow result, and view that run again from history without breaking the terminal interface.
