# Day045 Local Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local browser operator console that submits client briefs to the existing three-Agent workflow and displays saved results.

**Architecture:** A Python standard-library HTTP server serves one HTML file and three JSON endpoints. It reuses the existing workflow entry and history functions; `main.py` remains the single source of Agent construction but becomes safe to import without launching the terminal loop.

**Tech Stack:** Python 3 standard library (`http.server`, `json`, `urllib`), native HTML/CSS/JavaScript, existing OpenAI Agents SDK and SQLite modules.

**Spec:** `docs/superpowers/specs/2026-09-05-day045-local-web-ui-design.md`

## Global Constraints

- Listen only on `127.0.0.1`.
- Add no dependencies.
- Reuse the existing Research → Strategy → Client Project Manager workflow.
- Reuse the existing workflow-history database and security checks.
- Do not add chat, streaming, authentication, public deployment, queues, or billing.
- Tests must not call the OpenAI API.
- Run full project verification once after implementation.

---

## File Map

- Modify `main.py`: move terminal-only startup into `run_cli()` and guard it with `if __name__ == "__main__"`.
- Create `web_app.py`: local HTTP server, request validation, JSON serialization, and route handling.
- Create `web/index.html`: accessible operator form, execution result, workflow steps, and history/detail UI.
- Create `test_web_app.py`: import-safety and local HTTP endpoint tests using stubs.
- Modify `verify_project.py`: include `web_app.py` in source compilation.
- Modify `PROGRESS.md`: record Day045 completion only after verification passes.

---

### Task 1: Make the Existing Runtime Safe to Import

**Files:**
- Create: `test_web_app.py`
- Modify: `main.py:211-442`

**Interfaces:**
- Consumes: existing global `main_agent` and `task_handlers`.
- Produces: `run_cli() -> None`; importing `main` must not call `input()` or print CLI startup text.

- [ ] **Step 1: Write the failing import-safety check**

Create `test_web_app.py` with:

```python
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_DIRECTORY = Path(__file__).resolve().parent


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_DIRECTORY)
    imported = subprocess.run(
        [sys.executable, "-c", "import main; print('imported')"],
        cwd=temp_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

assert imported.returncode == 0, imported.stderr
assert imported.stdout.strip() == "imported"
```

- [ ] **Step 2: Run the check and confirm the current CLI startup fails it**

Run: `python test_web_app.py`

Expected: FAIL because importing `main.py` currently prints startup output or attempts to read terminal input.

- [ ] **Step 3: Move terminal-only work behind `run_cli()`**

In `main.py`, leave Agent and tool construction at module scope. Move the project-memory prints, `SQLiteSession` construction, startup print, and the complete existing `while True` command loop into this structure:

```python
def run_cli():
    print(
        "Loaded project:",
        get_memory("project", "project_name")
    )
    print(read_memories())

    session = SQLiteSession(
        session_id="main_session",
        db_path="agent_memory.db"
    )
    print("Main Agent 已启动。输入 exit 结束。")

    while True:
        raw_input = input("\nYou: ")
        user_input = normalize_user_input(raw_input)


if __name__ == "__main__":
    run_cli()
```

Mechanical requirement: indent the existing command-loop body under `run_cli()` without changing branch order, messages, or behavior. Remove the former module-scope memory prints and `session` assignment after relocating them.

- [ ] **Step 4: Run focused and existing Main checks**

Run:

```powershell
python test_web_app.py
python test_main_task_entry.py
python test_main_workflow_entry.py
python test_main_workflow_history.py
```

Expected: all commands exit `0`; `test_web_app.py` prints no success line yet.

- [ ] **Step 5: Commit the import-safe runtime**

```powershell
git add main.py test_web_app.py
git commit -m "refactor: make Main runtime import safe"
```

---

### Task 2: Add the Local JSON API

**Files:**
- Create: `web_app.py`
- Modify: `test_web_app.py`

**Interfaces:**
- Consumes: `execute_workflow_request(user_input, handlers)`, `get_workflow_history(limit=10)`, `get_workflow_run(workflow_id)`, and `main.task_handlers` at server startup.
- Produces: `build_request_handler(handlers, execute_workflow, list_runs, read_run, index_path) -> type[BaseHTTPRequestHandler]` and `run_server(host="127.0.0.1", port=8000) -> None`.

- [ ] **Step 1: Extend the test with a stubbed local server**

Append these imports and checks to `test_web_app.py`:

```python
import json
import threading
from dataclasses import asdict
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from task_contract import AgentResult
from web_app import build_request_handler
from workflow_contract import WorkflowResult


def request_json(base_url, path, method="GET", payload=None):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        base_url + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))

    with response:
        return response.status, json.loads(response.read().decode("utf-8"))


workflow = WorkflowResult(
    workflow_id="workflow-web-test",
    workflow_type="client_project",
    status="completed",
    steps=[
        AgentResult(
            task_id="task-research",
            agent_name="Search Agent",
            status="completed",
            output="Research output",
        )
    ],
    final_output="Project output",
)
workflow_record = {
    **asdict(workflow),
    "objective": "Build a restaurant landing page",
    "context": "Kuala Lumpur restaurant",
    "created_at": "2026-09-05 12:00:00",
}
received_commands = []
stub_handlers = {"Search Agent": object()}


def fake_execute(command, handlers):
    received_commands.append((command, handlers))
    return workflow


def fake_list_runs(limit=10):
    assert limit == 10
    return [
        {
            "created_at": workflow_record["created_at"],
            "workflow_id": workflow_record["workflow_id"],
            "workflow_type": workflow_record["workflow_type"],
            "status": workflow_record["status"],
            "objective": workflow_record["objective"],
        }
    ]


def fake_read_run(workflow_id):
    if workflow_id == workflow_record["workflow_id"]:
        return workflow_record
    return None


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
    index_path = Path(temp_dir) / "index.html"
    index_path.write_text("<h1>AI Agency Operator</h1>", encoding="utf-8")
    handler = build_request_handler(
        stub_handlers,
        execute_workflow=fake_execute,
        list_runs=fake_list_runs,
        read_run=fake_read_run,
        index_path=index_path,
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        status, created = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload={
                "objective": "Build a restaurant landing page",
                "context": "Kuala Lumpur restaurant",
            },
        )
        assert status == 200
        assert created["workflow_id"] == workflow.workflow_id
        assert received_commands == [
            (
                "客户项目：Build a restaurant landing page | "
                "Kuala Lumpur restaurant",
                stub_handlers,
            )
        ]

        status, error = request_json(
            base_url,
            "/api/workflows",
            method="POST",
            payload={"objective": " ", "context": "context"},
        )
        assert status == 400
        assert error["error"] == "objective cannot be empty."

        status, history = request_json(base_url, "/api/workflows")
        assert status == 200
        assert history["runs"][0]["workflow_id"] == workflow.workflow_id

        status, detail = request_json(
            base_url,
            "/api/workflows/workflow-web-test",
        )
        assert status == 200
        assert detail["final_output"] == "Project output"

        status, missing = request_json(
            base_url,
            "/api/workflows/missing",
        )
        assert status == 404
        assert missing["error"] == "Workflow not found."
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
```

- [ ] **Step 2: Run the test and confirm the missing backend fails**

Run: `python test_web_app.py`

Expected: FAIL because `web_app.py` or `build_request_handler()` does not exist.

- [ ] **Step 3: Implement the minimal standard-library server**

Create `web_app.py`:

```python
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from workflow_entry import execute_workflow_request
from workflow_history import get_workflow_history, get_workflow_run


HOST = "127.0.0.1"
PORT = 8000
MAX_BODY_BYTES = 64_000
INDEX_PATH = Path(__file__).resolve().parent / "web" / "index.html"


def build_request_handler(
    handlers,
    execute_workflow=execute_workflow_request,
    list_runs=get_workflow_history,
    read_run=get_workflow_run,
    index_path=INDEX_PATH,
):
    class RequestHandler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/":
                try:
                    body = Path(index_path).read_bytes()
                except OSError:
                    self.send_json(500, {"error": "Web interface unavailable."})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/api/workflows":
                self.send_json(200, {"runs": list_runs(limit=10)})
                return

            prefix = "/api/workflows/"
            if path.startswith(prefix):
                workflow_id = unquote(path[len(prefix):]).strip()
                if not workflow_id:
                    self.send_json(400, {"error": "workflow_id cannot be empty."})
                    return

                record = read_run(workflow_id)
                if record is None:
                    self.send_json(404, {"error": "Workflow not found."})
                    return

                self.send_json(200, record)
                return

            self.send_json(404, {"error": "Not found."})

        def do_POST(self):
            if urlparse(self.path).path != "/api/workflows":
                self.send_json(404, {"error": "Not found."})
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_json(400, {"error": "Invalid Content-Length."})
                return

            if content_length <= 0 or content_length > MAX_BODY_BYTES:
                self.send_json(400, {"error": "Invalid request size."})
                return

            try:
                payload = json.loads(
                    self.rfile.read(content_length).decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_json(400, {"error": "Invalid JSON."})
                return

            if not isinstance(payload, dict):
                self.send_json(400, {"error": "JSON body must be an object."})
                return

            values = {}
            for field in ("objective", "context"):
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.send_json(400, {"error": f"{field} cannot be empty."})
                    return
                values[field] = value.strip()

            command = (
                f"客户项目：{values['objective']} | {values['context']}"
            )

            try:
                result = execute_workflow(command, handlers)
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
                return
            except Exception:
                self.send_json(500, {"error": "Workflow execution failed."})
                return

            self.send_json(200, asdict(result))

        def log_message(self, format, *args):
            return

    return RequestHandler


def run_server(host=HOST, port=PORT):
    from main import task_handlers

    server = HTTPServer(
        (host, port),
        build_request_handler(task_handlers),
    )
    print(f"AI Agency Operator: http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
```

- [ ] **Step 4: Run the API check**

Run: `python test_web_app.py`

Expected: exit `0` with no API call.

- [ ] **Step 5: Commit the API**

```powershell
git add web_app.py test_web_app.py
git commit -m "feat: add local workflow API"
```

---

### Task 3: Add the Operator Console

**Files:**
- Create: `web/index.html`
- Modify: `test_web_app.py`

**Interfaces:**
- Consumes: `POST /api/workflows`, `GET /api/workflows`, and `GET /api/workflows/{workflow_id}`.
- Produces: one responsive page with form, status, result steps, history, and detail selection.

- [ ] **Step 1: Add a page-delivery assertion**

Inside the existing temporary-server `try` block in `test_web_app.py`, before the JSON requests, add:

```python
with urlopen(base_url + "/", timeout=5) as response:
    page = response.read().decode("utf-8")

assert response.status == 200
assert "AI Agency Operator" in page
assert 'id="client-form"' in page
assert 'id="history-list"' in page
```

Change the temporary `index_path.write_text(...)` fixture to read the production page:

```python
index_path = PROJECT_DIRECTORY / "web" / "index.html"
```

- [ ] **Step 2: Run the test and confirm the missing page fails**

Run: `python test_web_app.py`

Expected: FAIL because `web/index.html` does not exist.

- [ ] **Step 3: Create the single-file frontend**

Create `web/index.html` with semantic HTML and these exact DOM contracts:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Agency Operator</title>
  <style>
    :root { color-scheme: dark; --bg:#0b0d10; --panel:#14171c; --line:#282d35; --text:#f4f6f8; --muted:#9aa4b2; --accent:#80ffb0; --danger:#ff7b7b; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 system-ui,sans-serif; }
    main { width:min(1180px,calc(100% - 32px)); margin:0 auto; padding:32px 0 56px; }
    header { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:24px; }
    h1,h2,p { margin-top:0; }
    h1 { font-size:clamp(1.7rem,4vw,2.7rem); letter-spacing:-.04em; }
    h2 { font-size:1rem; }
    .status { color:var(--accent); font-size:.9rem; }
    .grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.25fr); gap:18px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:20px; }
    label { display:block; margin:16px 0 6px; color:var(--muted); font-size:.9rem; }
    input,textarea,button { width:100%; font:inherit; }
    input,textarea { border:1px solid var(--line); border-radius:10px; background:#0f1216; color:var(--text); padding:12px; }
    textarea { min-height:180px; resize:vertical; }
    button { border:0; border-radius:10px; padding:12px 16px; background:var(--accent); color:#07120b; font-weight:750; cursor:pointer; }
    button:disabled { opacity:.55; cursor:wait; }
    .muted { color:var(--muted); }
    .error { color:var(--danger); }
    .steps,.history { display:grid; gap:10px; }
    .step,.history button { border:1px solid var(--line); border-radius:10px; background:#0f1216; color:var(--text); padding:12px; text-align:left; }
    .step strong,.history strong { display:block; margin-bottom:4px; }
    .history button { cursor:pointer; }
    .history button:hover { border-color:var(--accent); }
    .wide { grid-column:1/-1; }
    pre { white-space:pre-wrap; word-break:break-word; font:inherit; }
    @media (max-width:760px) { .grid { grid-template-columns:1fr; } header { align-items:flex-start; flex-direction:column; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div><p class="muted">LOCAL OPERATIONS</p><h1>AI Agency Operator</h1></div>
      <div class="status">● 127.0.0.1</div>
    </header>
    <section class="grid">
      <form id="client-form" class="panel">
        <h2>启动客户项目</h2>
        <label for="objective">客户目标</label>
        <input id="objective" name="objective" required placeholder="例如：为餐厅建立获客落地页">
        <label for="context">项目背景</label>
        <textarea id="context" name="context" required placeholder="客户、受众、产品、限制与已知事实"></textarea>
        <p id="form-message" class="muted" aria-live="polite"></p>
        <button id="submit-button" type="submit">运行工作流</button>
      </form>
      <section class="panel" aria-live="polite">
        <h2>执行结果</h2>
        <p id="result-status" class="muted">等待提交客户项目。</p>
        <pre id="final-output"></pre>
        <div id="result-steps" class="steps"></div>
      </section>
      <section class="panel wide">
        <h2>最近项目</h2>
        <div id="history-list" class="history"><p class="muted">正在读取记录…</p></div>
      </section>
    </section>
  </main>
  <script>
    const form = document.querySelector('#client-form');
    const button = document.querySelector('#submit-button');
    const message = document.querySelector('#form-message');
    const status = document.querySelector('#result-status');
    const output = document.querySelector('#final-output');
    const steps = document.querySelector('#result-steps');
    const history = document.querySelector('#history-list');

    async function api(path, options) {
      const response = await fetch(path, options);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '请求失败。');
      return payload;
    }

    function renderRun(run) {
      status.textContent = run.status === 'completed' ? '工作流已完成' : `工作流失败：${run.error || '未知错误'}`;
      status.className = run.status === 'completed' ? 'status' : 'error';
      output.textContent = run.final_output || '';
      steps.replaceChildren();
      for (const item of run.steps || []) {
        const card = document.createElement('article');
        card.className = 'step';
        const title = document.createElement('strong');
        title.textContent = `${item.agent_name} · ${item.status}`;
        const text = document.createElement('div');
        text.textContent = item.output || item.error || '';
        card.append(title, text);
        steps.append(card);
      }
    }

    async function loadRun(workflowId) {
      try { renderRun(await api(`/api/workflows/${encodeURIComponent(workflowId)}`)); }
      catch (error) { status.textContent = error.message; status.className = 'error'; }
    }

    async function loadHistory() {
      try {
        const payload = await api('/api/workflows');
        history.replaceChildren();
        if (!payload.runs.length) {
          const empty = document.createElement('p');
          empty.className = 'muted';
          empty.textContent = '暂无项目记录。';
          history.append(empty);
          return;
        }
        for (const run of payload.runs) {
          const item = document.createElement('button');
          item.type = 'button';
          const title = document.createElement('strong');
          title.textContent = run.objective;
          const meta = document.createElement('span');
          meta.className = 'muted';
          meta.textContent = `${run.created_at} · ${run.status}`;
          item.append(title, meta);
          item.addEventListener('click', () => loadRun(run.workflow_id));
          history.append(item);
        }
      } catch (error) {
        history.textContent = error.message;
        history.className = 'history error';
      }
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      button.disabled = true;
      message.textContent = 'Research → Strategy → Project Manager 执行中…';
      message.className = 'muted';
      try {
        const run = await api('/api/workflows', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            objective: form.objective.value,
            context: form.context.value,
          }),
        });
        renderRun(run);
        message.textContent = '项目已保存。';
        await loadHistory();
      } catch (error) {
        message.textContent = error.message;
        message.className = 'error';
      } finally {
        button.disabled = false;
      }
    });

    loadHistory();
  </script>
</body>
</html>
```

- [ ] **Step 4: Run the complete focused test**

Run: `python test_web_app.py`

Expected: exit `0`.

- [ ] **Step 5: Commit the page**

```powershell
git add web/index.html test_web_app.py
git commit -m "feat: add AI Agency operator console"
```

---

### Task 4: Register, Verify, and Record Day045

**Files:**
- Modify: `verify_project.py:7-27`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `web_app.py` and all discovered `test_*.py` scripts.
- Produces: one passing full verification and a Day045 progress record.

- [ ] **Step 1: Register the backend source**

Add this entry once to `SOURCE_FILE_NAMES` in `verify_project.py`:

```python
    "web_app.py",
```

- [ ] **Step 2: Run the full verification once**

Run: `python verify_project.py`

Expected:

```text
[PASS] compile web_app.py
[PASS] test_web_app.py
Summary: 41/41 tests passed.
```

If the discovered count differs because another test was added independently, require every discovered test to pass and record the actual count.

- [ ] **Step 3: Perform the local smoke check**

Run: `python web_app.py`

Open `http://127.0.0.1:8000`, confirm the form and history load, submit one non-sensitive client brief, open the newly saved history record, then stop the server with `Ctrl+C`.

- [ ] **Step 4: Record completion**

Append to `PROGRESS.md`, using the actual verification count:

```markdown

## Day045 — Complete

- Added a local browser operator console for structured client briefs.
- Reused the existing Research → Strategy → Client Project Manager workflow.
- Added workflow result, Agent-step, history, and detail views.
- Kept the terminal interface working and added no dependencies.
- Verification: `python verify_project.py` — 41/41 tests passed.
```

- [ ] **Step 5: Commit the verified feature**

```powershell
git add verify_project.py PROGRESS.md
git commit -m "docs: complete Day045 local web UI"
```

- [ ] **Step 6: Confirm final repository state**

Run:

```powershell
git status --short
git log -5 --oneline
```

Expected: empty status and five Day045 commits: design, import-safe runtime, API, page, and completion record.
