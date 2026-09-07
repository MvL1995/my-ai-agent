import json
import sqlite3
from contextlib import closing
from dataclasses import asdict

from landing_page_package import parse_landing_page_package
from memory import DB_PATH, contains_sensitive_memory


SENSITIVE_WORKFLOW_ERROR = "拒绝工作流：检测到密码、API Key、Token 或密钥。"


def init_workflow_history_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                workflow_id TEXT PRIMARY KEY,
                workflow_type TEXT NOT NULL,
                objective TEXT NOT NULL,
                context TEXT NOT NULL,
                status TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                final_output TEXT NOT NULL,
                error TEXT,
                retry_of TEXT,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(workflow_runs)")
        }
        if "retry_of" not in columns:
            conn.execute("ALTER TABLE workflow_runs ADD COLUMN retry_of TEXT")
        if "attempt_number" not in columns:
            conn.execute(
                "ALTER TABLE workflow_runs ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 1"
            )


def save_workflow_run(objective, context, result):
    persisted_text = [
        objective,
        context,
        result.workflow_id,
        result.workflow_type,
        result.status,
        result.final_output,
        result.error or "",
    ]
    for step in result.steps:
        persisted_text.extend([
            step.task_id,
            step.agent_name,
            step.status,
            step.output,
            step.error or "",
        ])

    if any(contains_sensitive_memory(value) for value in persisted_text):
        raise ValueError(SENSITIVE_WORKFLOW_ERROR)

    try:
        steps_json = json.dumps(
            [asdict(step) for step in result.steps], ensure_ascii=False
        )
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            conn.execute(
                """
                INSERT INTO workflow_runs (
                    workflow_id, workflow_type, objective, context, status,
                    steps_json, final_output, error, retry_of, attempt_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.workflow_id,
                    result.workflow_type,
                    objective,
                    context,
                    result.status,
                    steps_json,
                    result.final_output,
                    result.error,
                    result.retry_of,
                    result.attempt_number,
                ),
            )
    except (sqlite3.Error, TypeError) as error:
        raise RuntimeError("工作流已执行，但历史保存失败。") from error


def get_workflow_history(limit=10):
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer.")

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        rows = conn.execute(
            """
            SELECT created_at, workflow_id, workflow_type, status, objective,
                   retry_of, attempt_number
            FROM workflow_runs
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "created_at": row[0],
            "workflow_id": row[1],
            "workflow_type": row[2],
            "status": row[3],
            "objective": row[4],
            "retry_of": row[5],
            "attempt_number": row[6],
        }
        for row in rows
    ]


def get_next_attempt_number(root_workflow_id):
    if not isinstance(root_workflow_id, str) or not root_workflow_id.strip():
        raise ValueError("root_workflow_id cannot be empty.")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0) + 1
            FROM workflow_runs
            WHERE workflow_id = ? OR retry_of = ?
            """,
            (root_workflow_id, root_workflow_id),
        ).fetchone()[0]


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


def _workflow_diagnostics(steps):
    return {
        "duration_ms": sum(step.get("duration_ms", 0) for step in steps),
        "failed_stage": next((
            step.get("agent_name") for step in reversed(steps)
            if step.get("status") == "failed"
        ), None),
    }


def get_workflow_run(workflow_id):
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty.")

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        row = conn.execute(
            """
            SELECT workflow_id, workflow_type, objective, context, status,
                   steps_json, final_output, error, retry_of, attempt_number, created_at
            FROM workflow_runs
            WHERE workflow_id = ?
            """,
            (workflow_id,),
        ).fetchone()
        if row is None:
            return None
        root_workflow_id = row[8] or row[0]
        attempt_rows = conn.execute(
            """
            SELECT workflow_id, status, attempt_number, steps_json
            FROM workflow_runs
            WHERE workflow_id = ? OR retry_of = ?
            ORDER BY attempt_number, rowid
            """,
            (root_workflow_id, root_workflow_id),
        ).fetchall()

    steps = json.loads(row[5])

    attempts = []
    for attempt in attempt_rows:
        attempt_steps = json.loads(attempt[3])
        attempts.append({
            "workflow_id": attempt[0],
            "status": attempt[1],
            "attempt_number": attempt[2],
            **_workflow_diagnostics(attempt_steps),
        })

    return {
        "workflow_id": row[0],
        "workflow_type": row[1],
        "objective": row[2],
        "context": row[3],
        "status": row[4],
        "steps": steps,
        "landing_page": _landing_page_from_steps(steps),
        "retry_of": row[8],
        "attempt_number": row[9],
        "attempts": attempts,
        "final_output": row[6],
        "error": row[7],
        **_workflow_diagnostics(steps),
        "created_at": row[10],
    }
