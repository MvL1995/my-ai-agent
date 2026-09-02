import json
import sqlite3
from contextlib import closing
from dataclasses import asdict

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_workflow_run(objective, context, result):
    persisted_text = [objective, context, result.final_output, result.error or ""]
    for step in result.steps:
        persisted_text.extend([step.output, step.error or ""])

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
                    steps_json, final_output, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            SELECT created_at, workflow_id, workflow_type, status, objective
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
        }
        for row in rows
    ]


def get_workflow_run(workflow_id):
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty.")

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        row = conn.execute(
            """
            SELECT workflow_id, workflow_type, objective, context, status,
                   steps_json, final_output, error, created_at
            FROM workflow_runs
            WHERE workflow_id = ?
            """,
            (workflow_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "workflow_id": row[0],
        "workflow_type": row[1],
        "objective": row[2],
        "context": row[3],
        "status": row[4],
        "steps": json.loads(row[5]),
        "final_output": row[6],
        "error": row[7],
        "created_at": row[8],
    }
