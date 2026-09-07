import json
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import asdict

from landing_page_package import parse_landing_page_package
from memory import DB_PATH, contains_sensitive_memory


# ponytail: fixed local threshold; use confidence intervals when volume grows.
MIN_DECISION_SAMPLES = 3
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


def _measured_duration(steps):
    if not steps or any("duration_ms" not in step for step in steps):
        return None
    return sum(step["duration_ms"] for step in steps)


def _failure_decision(status, failed_stage, error):
    if status != "failed":
        return {
            "failure_type": None,
            "retry_recommended": False,
            "recommended_action": None,
        }

    normalized_error = (error or "").casefold()
    if any(marker in normalized_error for marker in (
        "permission denied", "unauthorized", "forbidden",
        "authentication", "权限",
    )):
        return {
            "failure_type": "configuration",
            "retry_recommended": False,
            "recommended_action": "先修复配置或权限，再执行。",
        }
    if any(marker in normalized_error for marker in (
        "必须返回", "不能为空", "invalid json",
        "validation", "校验", "缺少",
    )):
        return {
            "failure_type": "validation",
            "retry_recommended": False,
            "recommended_action": "先修正输出格式，再执行。",
        }
    if any(marker in normalized_error for marker in (
        "暂时", "timeout", "timed out", "rate limit", "429",
        "unavailable", "connection", "network", "网络", "连接",
    )):
        return {
            "failure_type": "transient",
            "retry_recommended": True,
            "recommended_action": "建议重跑：临时故障通常可恢复。",
        }
    if failed_stage == "Search Agent":
        return {
            "failure_type": "external_dependency",
            "retry_recommended": True,
            "recommended_action": "建议重跑：Search Agent 外部依赖可能恢复。",
        }
    return {
        "failure_type": "execution",
        "retry_recommended": False,
        "recommended_action": "先检查失败详情，再决定是否重跑。",
    }


def get_retry_effectiveness():
    # ponytail: local history is small; move aggregation to SQL if volume grows.
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            """
            SELECT workflow_id, retry_of, status, attempt_number, steps_json,
                   error
            FROM workflow_runs
            ORDER BY rowid
            """
        ).fetchall()

    chains = {}
    for workflow_id, retry_of, status, attempt_number, steps_json, error in rows:
        chain = chains.setdefault(retry_of or workflow_id, [])
        chain.append((attempt_number, status, steps_json, error))

    retry_chains = 0
    recovered_chains = 0
    duration_changes = []
    failed_stages = Counter()
    retry_recommendations = 0
    accepted_recommendations = 0
    recommendation_hits = 0
    breakdown_by_decision = {}
    for chain in chains.values():
        chain.sort(key=lambda attempt: attempt[0])
        attempts = []
        for index, (_, status, steps_json, error) in enumerate(chain):
            steps = json.loads(steps_json)
            diagnostics = _workflow_diagnostics(steps)
            attempts.append((
                status,
                diagnostics,
                _measured_duration(steps),
            ))
            decision = _failure_decision(
                status, diagnostics["failed_stage"], error
            )
            if decision["retry_recommended"]:
                breakdown_key = (
                    decision["failure_type"], diagnostics["failed_stage"]
                )
                breakdown = breakdown_by_decision.setdefault(
                    breakdown_key,
                    {
                        "failure_type": decision["failure_type"],
                        "failed_stage": diagnostics["failed_stage"],
                        "recommendations": 0,
                        "accepted": 0,
                        "hits": 0,
                    },
                )
                retry_recommendations += 1
                breakdown["recommendations"] += 1
                if index + 1 < len(chain):
                    accepted_recommendations += 1
                    breakdown["accepted"] += 1
                    is_hit = chain[index + 1][1] == "completed"
                    recommendation_hits += is_hit
                    breakdown["hits"] += is_hit

        if len(chain) < 2:
            continue
        retry_chains += 1
        recovered_chains += attempts[-1][0] == "completed"
        first_duration = attempts[0][2]
        latest_duration = attempts[-1][2]
        if first_duration is not None and latest_duration is not None:
            duration_changes.append(latest_duration - first_duration)
        failed_stages.update(
            diagnostics["failed_stage"]
            for _, diagnostics, _ in attempts
            if diagnostics["failed_stage"]
        )

    decision_breakdown = list(breakdown_by_decision.values())
    for breakdown in decision_breakdown:
        breakdown["hit_rate"] = (
            round(breakdown["hits"] / breakdown["accepted"] * 100, 1)
            if breakdown["accepted"] else None
        )
        breakdown["sample_sufficient"] = (
            breakdown["accepted"] >= MIN_DECISION_SAMPLES
        )
    decision_breakdown.sort(key=lambda item: (
        item["hit_rate"] is None, item["hit_rate"] or 0,
        item["failure_type"], item["failed_stage"] or "",
    ))

    decision_metrics = {
        "retry_recommendations": retry_recommendations,
        "accepted_recommendations": accepted_recommendations,
        "recommendation_adoption_rate": (
            round(accepted_recommendations / retry_recommendations * 100, 1)
            if retry_recommendations else None
        ),
        "recommendation_hits": recommendation_hits,
        "decision_hit_rate": (
            round(recommendation_hits / accepted_recommendations * 100, 1)
            if accepted_recommendations else None
        ),
        "minimum_decision_samples": MIN_DECISION_SAMPLES,
        "decision_breakdown": decision_breakdown,
    }
    if not retry_chains:
        return {
            "retry_chains": 0,
            "recovered_chains": 0,
            "recovery_rate": None,
            "duration_samples": 0,
            "average_duration_change_ms": None,
            "top_failed_stage": None,
            **decision_metrics,
        }

    return {
        "retry_chains": retry_chains,
        "recovered_chains": recovered_chains,
        "recovery_rate": round(recovered_chains / retry_chains * 100, 1),
        "duration_samples": len(duration_changes),
        "average_duration_change_ms": (
            round(sum(duration_changes) / len(duration_changes), 2)
            if duration_changes else None
        ),
        "top_failed_stage": (
            failed_stages.most_common(1)[0][0]
            if failed_stages else None
        ),
        **decision_metrics,
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

    diagnostics = _workflow_diagnostics(steps)
    decision = _failure_decision(
        row[4], diagnostics["failed_stage"], row[7]
    )

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
        **diagnostics,
        **decision,
        "created_at": row[10],
    }
