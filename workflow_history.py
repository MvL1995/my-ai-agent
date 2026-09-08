import json
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import asdict

from landing_page_package import (
    parse_landing_page_package,
    validate_lead_capture_package,
)
from memory import DB_PATH, contains_sensitive_memory


# ponytail: fixed local thresholds; use confidence intervals when volume grows.
MIN_DECISION_SAMPLES = 3
MIN_RETRY_HIT_RATE = 50.0
RISK_LEVEL_HYSTERESIS = 10.0
CALIBRATED_RISK_LEVEL_HYSTERESIS = 15.0
RISK_LEVEL_JITTER_WINDOW = 3
MAX_RISK_LEVEL_JITTER_RATE = 25.0
SENSITIVE_WORKFLOW_ERROR = "拒绝工作流：检测到密码、API Key、Token 或密钥。"
MAX_ROLLBACK_REASON_LENGTH = 200


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
                override_source TEXT,
                override_reason TEXT,
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
        if "override_source" not in columns:
            conn.execute("ALTER TABLE workflow_runs ADD COLUMN override_source TEXT")
        if "override_reason" not in columns:
            conn.execute("ALTER TABLE workflow_runs ADD COLUMN override_reason TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_hysteresis_rollbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL DEFAULT 'rollback',
                failure_type TEXT NOT NULL,
                failed_stage TEXT,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                previous_hysteresis REAL NOT NULL,
                target_hysteresis REAL NOT NULL,
                execution_status TEXT NOT NULL,
                result_hysteresis REAL NOT NULL,
                workflow_rowid INTEGER NOT NULL,
                decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rollback_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(workflow_hysteresis_rollbacks)"
            )
        }
        if "action" not in rollback_columns:
            conn.execute(
                "ALTER TABLE workflow_hysteresis_rollbacks "
                "ADD COLUMN action TEXT NOT NULL DEFAULT 'rollback'"
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
        result.override_source or "",
        result.override_reason or "",
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
                    steps_json, final_output, error, retry_of, attempt_number,
                    override_source, override_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    result.override_source,
                    result.override_reason,
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
    for step in reversed(steps):
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

            try:
                package = validate_lead_capture_package(package)
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
                   error, override_source, rowid
            FROM workflow_runs
            ORDER BY rowid
            """
        ).fetchall()
        hysteresis_rows = conn.execute(
            """
            SELECT failure_type, failed_stage, decision, reason,
                   previous_hysteresis, target_hysteresis, execution_status,
                   result_hysteresis, workflow_rowid, decided_at, action
            FROM workflow_hysteresis_rollbacks
            ORDER BY id DESC
            """
        ).fetchall()
    manual_overrides = sum(bool(row[6]) for row in rows)
    successful_overrides = sum(
        bool(row[6]) and row[2] == "completed" for row in rows
    )
    runs_by_id = {row[0]: row for row in rows}
    run_rowids = {row[0]: row[7] for row in rows}
    hysteresis_decision_audit = [
        {
            "failure_type": row[0],
            "failed_stage": row[1],
            "decision": row[2],
            "reason": row[3],
            "previous_hysteresis": row[4],
            "target_hysteresis": row[5],
            "execution_status": row[6],
            "result_hysteresis": row[7],
            "workflow_rowid": row[8],
            "decided_at": row[9],
            "effectiveness": None,
            "action": row[10],
        }
        for row in hysteresis_rows
    ]
    hysteresis_rollback_audit = [
        item for item in hysteresis_decision_audit
        if item["action"] == "rollback"
    ]
    hysteresis_restoration_audit = [
        item for item in hysteresis_decision_audit
        if item["action"] == "restoration"
    ]
    hysteresis_reset_audit = [
        item for item in hysteresis_decision_audit
        if item["action"] == "reset"
    ]
    hysteresis_refreeze_audit = [
        item for item in hysteresis_decision_audit
        if item["action"] == "refreeze"
    ]
    latest_rollbacks = {}
    for rollback in hysteresis_rollback_audit:
        latest_rollbacks.setdefault(
            (rollback["failure_type"], rollback["failed_stage"]), rollback
        )

    latest_restorations = {}
    for restoration in hysteresis_restoration_audit:
        latest_restorations.setdefault(
            (restoration["failure_type"], restoration["failed_stage"]),
            restoration,
        )
    latest_refreezes = {}
    for refreeze in hysteresis_refreeze_audit:
        latest_refreezes.setdefault(
            (refreeze["failure_type"], refreeze["failed_stage"]), refreeze
        )
    latest_resets = {}
    for reset in hysteresis_reset_audit:
        latest_resets.setdefault(
            (reset["failure_type"], reset["failed_stage"]), reset
        )

    override_breakdown_by_failure = {}
    for row in rows:
        if not row[6]:
            continue
        source = runs_by_id.get(row[6])
        if source:
            source_diagnostics = _workflow_diagnostics(json.loads(source[4]))
            failure_type = _failure_decision(
                source[2], source_diagnostics["failed_stage"], source[5]
            )["failure_type"] or "unknown"
            failed_stage = source_diagnostics["failed_stage"]
        else:
            failure_type = "unknown"
            failed_stage = None
        breakdown = override_breakdown_by_failure.setdefault(
            (failure_type, failed_stage),
            {
                "failure_type": failure_type,
                "failed_stage": failed_stage,
                "overrides": 0,
                "successful": 0,
            },
        )
        breakdown["overrides"] += 1
        breakdown["successful"] += row[2] == "completed"

    chains = {}
    for workflow_id, retry_of, status, attempt_number, steps_json, error, override_source, _ in rows:
        chain = chains.setdefault(retry_of or workflow_id, [])
        chain.append((attempt_number, status, steps_json, error, override_source))

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
        for index, (_, status, steps_json, error, _) in enumerate(chain):
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
            next_is_override = index + 1 < len(chain) and bool(chain[index + 1][4])
            if decision["retry_recommended"] and not next_is_override:
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
    override_breakdown = list(override_breakdown_by_failure.values())
    for breakdown in override_breakdown:
        breakdown["success_rate"] = round(
            breakdown["successful"] / breakdown["overrides"] * 100, 1
        )
        breakdown["sample_sufficient"] = (
            breakdown["overrides"] >= MIN_DECISION_SAMPLES
        )
    override_breakdown.sort(key=lambda item: (
        item["success_rate"], item["failure_type"], item["failed_stage"] or "",
    ))
    # ponytail: retries are serial; persist events if branching is added.
    run_contexts = {}
    for row in rows:
        diagnostics = _workflow_diagnostics(json.loads(row[4]))
        decision = _failure_decision(
            row[2], diagnostics["failed_stage"], row[5]
        )
        run_contexts[row[0]] = (
            decision["failure_type"] or "unknown",
            diagnostics["failed_stage"],
            decision["retry_recommended"],
        )

    decision_history = {}
    override_history = {}
    latest_attempts = {}
    warned_workflows = set()
    risk_breakdown_by_failure = {}
    adopted_warnings = set()
    risk_warning_overrides = 0
    risk_warning_recoveries = 0
    risk_level_transitions = []
    last_risk_transitions = {}

    def has_risk_warning(row):
        context = run_contexts[row[0]]
        decision_samples = decision_history.get(context[:2])
        override_samples = override_history.get(context[:2])
        return bool(
            context[2]
            and decision_samples
            and decision_samples[0] >= MIN_DECISION_SAMPLES
            and decision_samples[1] * 100
            < decision_samples[0] * MIN_RETRY_HIT_RATE
            and override_samples
            and override_samples[0] >= MIN_DECISION_SAMPLES
            and override_samples[1] * 100
            < override_samples[0] * MIN_RETRY_HIT_RATE
        )

    def summarize_calibration(periods):
        summary = {}
        for name in ("before", "after"):
            period = periods[name]
            events = period["events"]
            summary[name] = {
                **period,
                "change_rate": (
                    round(period["changes"] / events * 100, 1)
                    if events else None
                ),
                "jitter_event_rate": (
                    round(period["jitters"] / events * 100, 1)
                    if events else None
                ),
            }
        sample_sufficient = (
            periods["after"]["events"] >= MIN_DECISION_SAMPLES
        )
        summary["sample_sufficient"] = sample_sufficient
        summary["effective"] = (
            summary["after"]["jitter_event_rate"]
            < summary["before"]["jitter_event_rate"]
            and summary["after"]["change_rate"]
            <= summary["before"]["change_rate"]
            if sample_sufficient else None
        )
        return summary

    def current_stability_period(breakdown):
        if breakdown["_reset_active"]:
            return breakdown["_reset_period"]
        if breakdown["_restoration_active"]:
            return breakdown["_restoration_period"]
        if breakdown["_rollback_active"]:
            return breakdown["_rollback_period"]
        period_name = (
            "after" if breakdown["hysteresis_calibrated"] else "before"
        )
        return breakdown["_calibration_periods"][period_name]

    def update_risk_level(breakdown, workflow_id):
        if (
            breakdown["warnings"] < MIN_DECISION_SAMPLES
            or breakdown["overrides"] < MIN_DECISION_SAMPLES
        ):
            return
        adoption_rate = round(
            breakdown["overrides"] / breakdown["warnings"] * 100, 1
        )
        recovery_rate = round(
            breakdown["recoveries"] / breakdown["overrides"] * 100, 1
        )
        current_level = breakdown["risk_level"]
        next_level = current_level
        hysteresis = breakdown["hysteresis"]
        if current_level == "high":
            if (
                breakdown["overrides"] * 100
                < breakdown["warnings"] * (MIN_RETRY_HIT_RATE - hysteresis)
                or breakdown["recoveries"] * 100
                >= breakdown["overrides"] * (MIN_RETRY_HIT_RATE + hysteresis)
            ):
                next_level = "medium"
        elif (
            breakdown["overrides"] * 100
            >= breakdown["warnings"] * MIN_RETRY_HIT_RATE
            and breakdown["recoveries"] * 100
            < breakdown["overrides"] * MIN_RETRY_HIT_RATE
        ):
            next_level = "high"
        if next_level == current_level:
            return

        key = (breakdown["failure_type"], breakdown["failed_stage"])
        previous = last_risk_transitions.get(key)
        is_jitter = bool(
            previous
            and previous[1] == next_level
            and breakdown["risk_events"] - previous[0]
            <= RISK_LEVEL_JITTER_WINDOW
        )
        breakdown["risk_level"] = next_level
        breakdown["level_changes"] += 1
        breakdown["jitters"] += is_jitter
        period = current_stability_period(breakdown)
        period["changes"] += 1
        period["jitters"] += is_jitter
        risk_level_transitions.append({
            "failure_type": breakdown["failure_type"],
            "failed_stage": breakdown["failed_stage"],
            "from_level": current_level,
            "to_level": next_level,
            "workflow_id": workflow_id,
            "warnings": breakdown["warnings"],
            "overrides": breakdown["overrides"],
            "adoption_rate": adoption_rate,
            "recoveries": breakdown["recoveries"],
            "recovery_rate": recovery_rate,
        })
        last_risk_transitions[key] = (
            breakdown["risk_events"], current_level, next_level
        )
        if (
            not breakdown["_rollback_active"] and
            breakdown["level_changes"] >= MIN_DECISION_SAMPLES
            and breakdown["jitters"] * 100
            >= breakdown["level_changes"] * MAX_RISK_LEVEL_JITTER_RATE
        ):
            breakdown["hysteresis"] = CALIBRATED_RISK_LEVEL_HYSTERESIS
            breakdown["hysteresis_calibrated"] = True

    def record_risk_event(breakdown, workflow_id):
        rollback = breakdown["_rollback"]
        restoration = breakdown["_restoration"]
        reset = breakdown["_reset"]
        if (
            reset
            and reset["decision"] == "approved"
            and run_rowids[workflow_id] > reset["workflow_rowid"]
        ):
            breakdown["hysteresis"] = reset["target_hysteresis"]
            breakdown["_rollback_active"] = False
            breakdown["_restoration_active"] = False
            breakdown["_reset_active"] = True
        elif (
            restoration
            and restoration["decision"] == "approved"
            and run_rowids[workflow_id] > restoration["workflow_rowid"]
        ):
            breakdown["hysteresis"] = restoration["target_hysteresis"]
            breakdown["_rollback_active"] = False
            breakdown["_restoration_active"] = True
        elif (
            rollback
            and rollback["decision"] == "approved"
            and run_rowids[workflow_id] > rollback["workflow_rowid"]
        ):
            breakdown["hysteresis"] = rollback["target_hysteresis"]
            breakdown["_rollback_active"] = True
        period = current_stability_period(breakdown)
        breakdown["risk_events"] += 1
        period["events"] += 1
        update_risk_level(breakdown, workflow_id)

    def record_risk_warning(row):
        context = run_contexts[row[0]]
        breakdown = risk_breakdown_by_failure.setdefault(
            context[:2],
            {
                "failure_type": context[0],
                "failed_stage": context[1],
                "warnings": 0,
                "overrides": 0,
                "recoveries": 0,
                "risk_level": "medium",
                "risk_events": 0,
                "level_changes": 0,
                "jitters": 0,
                "hysteresis": RISK_LEVEL_HYSTERESIS,
                "hysteresis_calibrated": False,
                "_rollback": latest_rollbacks.get(context[:2]),
                "_rollback_active": False,
                "_rollback_period": {
                    "events": 0, "changes": 0, "jitters": 0
                },
                "_restoration": latest_restorations.get(context[:2]),
                "_restoration_active": False,
                "_restoration_period": {
                    "events": 0, "changes": 0, "jitters": 0
                },
                "_reset": latest_resets.get(context[:2]),
                "_reset_active": False,
                "_reset_period": {
                    "events": 0, "changes": 0, "jitters": 0
                },
                "_calibration_periods": {
                    "before": {
                        "events": 0, "changes": 0, "jitters": 0
                    },
                    "after": {
                        "events": 0, "changes": 0, "jitters": 0
                    },
                },
            },
        )
        if row[0] not in warned_workflows:
            warned_workflows.add(row[0])
            breakdown["warnings"] += 1
            record_risk_event(breakdown, row[0])
        return breakdown

    for row in rows:
        root_workflow_id = row[1] or row[0]
        previous = latest_attempts.get(root_workflow_id)
        if row[6]:
            source = runs_by_id.get(row[6])
            if source and has_risk_warning(source):
                risk_breakdown = record_risk_warning(source)
                if source[0] not in adopted_warnings:
                    adopted_warnings.add(source[0])
                    risk_warning_overrides += 1
                    risk_warning_recoveries += row[2] == "completed"
                    risk_breakdown["overrides"] += 1
                    risk_breakdown["recoveries"] += row[2] == "completed"
                    record_risk_event(risk_breakdown, row[0])
            source_context = run_contexts.get(row[6], ("unknown", None))
            samples = override_history.setdefault(source_context[:2], [0, 0])
            samples[0] += 1
            samples[1] += row[2] == "completed"
        elif row[1] and previous:
            previous_context = run_contexts[previous[0]]
            if previous_context[2]:
                samples = decision_history.setdefault(
                    previous_context[:2], [0, 0]
                )
                samples[0] += 1
                samples[1] += row[2] == "completed"

        if has_risk_warning(row):
            record_risk_warning(row)
        latest_attempts[root_workflow_id] = row

    risk_warnings = len(warned_workflows)
    risk_warning_breakdown = list(risk_breakdown_by_failure.values())
    calibration_totals = {
        "before": {"events": 0, "changes": 0, "jitters": 0},
        "after": {"events": 0, "changes": 0, "jitters": 0},
    }
    for breakdown in risk_warning_breakdown:
        breakdown["adoption_rate"] = round(
            breakdown["overrides"] / breakdown["warnings"] * 100, 1
        )
        breakdown["recovery_rate"] = (
            round(
                breakdown["recoveries"] / breakdown["overrides"] * 100, 1
            )
            if breakdown["overrides"] else None
        )
        breakdown["sample_sufficient"] = (
            breakdown["warnings"] >= MIN_DECISION_SAMPLES
        )
        breakdown["change_rate"] = round(
            breakdown["level_changes"] / breakdown["risk_events"] * 100, 1
        )
        breakdown["jitter_rate"] = (
            round(
                breakdown["jitters"] / breakdown["level_changes"] * 100, 1
            )
            if breakdown["level_changes"] else None
        )
        periods = breakdown.pop("_calibration_periods")
        rollback_period = breakdown.pop("_rollback_period")
        restoration_period = breakdown.pop("_restoration_period")
        reset_period = breakdown.pop("_reset_period")
        rollback = breakdown.pop("_rollback")
        restoration = breakdown.pop("_restoration")
        reset = breakdown.pop("_reset")
        breakdown.pop("_rollback_active")
        breakdown.pop("_restoration_active")
        breakdown.pop("_reset_active")
        if rollback and rollback["decision"] == "approved":
            rollback["effectiveness"] = summarize_calibration({
                "before": periods["after"],
                "after": rollback_period,
            })
        if restoration and restoration["decision"] == "approved":
            restoration["effectiveness"] = summarize_calibration({
                "before": rollback_period,
                "after": restoration_period,
            })
        if reset and reset["decision"] == "approved":
            reset["effectiveness"] = summarize_calibration({
                "before": restoration_period,
                "after": reset_period,
            })
            reset_effectiveness = reset["effectiveness"]
            if reset_effectiveness["sample_sufficient"]:
                reset_effectiveness["effective"] = all(
                    reset_effectiveness["after"][metric]
                    <= reset_effectiveness["before"][metric]
                    for metric in ("change_rate", "jitter_event_rate")
                )
            breakdown["hysteresis"] = reset["target_hysteresis"]
        elif restoration and restoration["decision"] == "approved":
            breakdown["hysteresis"] = restoration["target_hysteresis"]
        elif rollback and rollback["decision"] == "approved":
            breakdown["hysteresis"] = rollback["target_hysteresis"]
        if breakdown["hysteresis_calibrated"]:
            for phase, values in periods.items():
                for metric, value in values.items():
                    calibration_totals[phase][metric] += value
        breakdown["calibration_effectiveness"] = (
            summarize_calibration(periods)
            if breakdown["hysteresis_calibrated"]
            else None
        )
    risk_warning_breakdown.sort(key=lambda item: (
        not item["sample_sufficient"], item["adoption_rate"],
        item["failure_type"], item["failed_stage"] or "",
    ))
    risk_level_events = sum(
        item["risk_events"] for item in risk_warning_breakdown
    )
    risk_level_changes = len(risk_level_transitions)
    risk_level_jitters = sum(
        item["jitters"] for item in risk_warning_breakdown
    )
    calibrated_hysteresis_groups = sum(
        item["hysteresis_calibrated"]
        for item in risk_warning_breakdown
    )
    risk_calibration_effectiveness = (
        summarize_calibration(calibration_totals)
        if calibrated_hysteresis_groups else None
    )
    ineffective_calibration_breakdown = []
    for breakdown in risk_warning_breakdown:
        effectiveness = breakdown["calibration_effectiveness"]
        rollback = latest_rollbacks.get(
            (breakdown["failure_type"], breakdown["failed_stage"])
        )
        if effectiveness and effectiveness["effective"] is False:
            item = {
                "failure_type": breakdown["failure_type"],
                "failed_stage": breakdown["failed_stage"],
                "current_hysteresis": breakdown["hysteresis"],
                "target_hysteresis": RISK_LEVEL_HYSTERESIS,
                "post_calibration_events": effectiveness["after"]["events"],
                "before_change_rate": effectiveness["before"]["change_rate"],
                "after_change_rate": effectiveness["after"]["change_rate"],
                "before_jitter_event_rate": (
                    effectiveness["before"]["jitter_event_rate"]
                ),
                "after_jitter_event_rate": (
                    effectiveness["after"]["jitter_event_rate"]
                ),
                "rollback_status": (
                    rollback["execution_status"]
                    if rollback and rollback["decision"] == "approved"
                    else rollback["decision"] if rollback
                    else "approval_required"
                ),
            }
            if rollback:
                item["decision_reason"] = rollback["reason"]
                item["rollback_effectiveness"] = rollback["effectiveness"]
                item["decided_at"] = rollback["decided_at"]
            ineffective_calibration_breakdown.append(item)
    ineffective_calibration_breakdown.sort(
        key=lambda item: (
            item["after_jitter_event_rate"]
            - item["before_jitter_event_rate"],
            item["after_change_rate"] - item["before_change_rate"],
        ),
        reverse=True,
    )


    ineffective_rollback_breakdown = []
    for rollback in hysteresis_rollback_audit:
        effectiveness = rollback["effectiveness"]
        restoration = latest_restorations.get((
            rollback["failure_type"], rollback["failed_stage"]
        ))
        if (
            rollback["decision"] == "approved"
            and rollback["execution_status"] == "completed"
            and effectiveness
            and effectiveness["effective"] is False
        ):
            item = {
                "failure_type": rollback["failure_type"],
                "failed_stage": rollback["failed_stage"],
                "current_hysteresis": (
                    restoration["result_hysteresis"]
                    if restoration else rollback["result_hysteresis"]
                ),
                "target_hysteresis": rollback["previous_hysteresis"],
                "post_rollback_events": effectiveness["after"]["events"],
                "before_change_rate": effectiveness["before"]["change_rate"],
                "after_change_rate": effectiveness["after"]["change_rate"],
                "before_jitter_event_rate": (
                    effectiveness["before"]["jitter_event_rate"]
                ),
                "after_jitter_event_rate": (
                    effectiveness["after"]["jitter_event_rate"]
                ),
                "restoration_status": (
                    restoration["execution_status"]
                    if restoration and restoration["decision"] == "approved"
                    else restoration["decision"] if restoration
                    else "approval_required"
                ),
            }
            if restoration:
                item["decision_reason"] = restoration["reason"]
                item["decided_at"] = restoration["decided_at"]
                item["restoration_effectiveness"] = (
                    restoration["effectiveness"]
                )
            ineffective_rollback_breakdown.append(item)
    ineffective_rollback_breakdown.sort(
        key=lambda item: (
            item["after_change_rate"] - item["before_change_rate"],
            item["after_jitter_event_rate"]
            - item["before_jitter_event_rate"],
        ),
        reverse=True,
    )

    ineffective_restoration_breakdown = []
    for restoration in hysteresis_restoration_audit:
        effectiveness = restoration["effectiveness"]
        reset = latest_resets.get((
            restoration["failure_type"], restoration["failed_stage"]
        ))
        refreeze = latest_refreezes.get((
            restoration["failure_type"], restoration["failed_stage"]
        ))
        if (
            restoration["decision"] == "approved"
            and restoration["execution_status"] == "completed"
            and effectiveness
            and effectiveness["effective"] is False
            and effectiveness["sample_sufficient"]
        ):
            ineffective_restoration_breakdown.append({
                "failure_type": restoration["failure_type"],
                "failed_stage": restoration["failed_stage"],
                "current_hysteresis": (
                    reset["result_hysteresis"] if reset
                    else restoration["result_hysteresis"]
                ),
                "target_hysteresis": restoration["result_hysteresis"],
                "post_restoration_events": (
                    effectiveness["after"]["events"]
                ),
                "before_change_rate": (
                    effectiveness["before"]["change_rate"]
                ),
                "after_change_rate": effectiveness["after"]["change_rate"],
                "before_jitter_event_rate": (
                    effectiveness["before"]["jitter_event_rate"]
                ),
                "after_jitter_event_rate": (
                    effectiveness["after"]["jitter_event_rate"]
                ),
                "cycle_status": (
                    "blocked"
                    if refreeze and refreeze["decision"] == "approved"
                    else "released"
                    if reset and reset["decision"] == "approved"
                    else "blocked"
                ),
                "reset_status": (
                    reset["execution_status"]
                    if reset and reset["decision"] == "approved"
                    else reset["decision"] if reset
                    else "approval_required"
                ),
                **(
                    {
                        "decision_reason": reset["reason"],
                        "decided_at": reset["decided_at"],
                        "reset_effectiveness": reset["effectiveness"],
                    } if reset else {}
                ),
            })
    ineffective_restoration_breakdown.sort(
        key=lambda item: (
            item["after_jitter_event_rate"]
            - item["before_jitter_event_rate"],
            item["after_change_rate"] - item["before_change_rate"],
        ),
        reverse=True,
    )

    ineffective_reset_breakdown = []
    for reset in hysteresis_reset_audit:
        effectiveness = reset["effectiveness"]
        refreeze = latest_refreezes.get((
            reset["failure_type"], reset["failed_stage"]
        ))
        if (
            reset["decision"] == "approved"
            and reset["execution_status"] == "completed"
            and effectiveness
            and effectiveness["sample_sufficient"]
            and effectiveness["effective"] is False
        ):
            ineffective_reset_breakdown.append({
                "failure_type": reset["failure_type"],
                "failed_stage": reset["failed_stage"],
                "current_hysteresis": reset["result_hysteresis"],
                "post_reset_events": effectiveness["after"]["events"],
                "before_change_rate": (
                    effectiveness["before"]["change_rate"]
                ),
                "after_change_rate": effectiveness["after"]["change_rate"],
                "before_jitter_event_rate": (
                    effectiveness["before"]["jitter_event_rate"]
                ),
                "after_jitter_event_rate": (
                    effectiveness["after"]["jitter_event_rate"]
                ),
                "cycle_status": (
                    "blocked"
                    if refreeze and refreeze["decision"] == "approved"
                    else "released"
                ),
                "refreeze_status": (
                    refreeze["execution_status"]
                    if refreeze and refreeze["decision"] == "approved"
                    else refreeze["decision"] if refreeze
                    else "approval_required"
                ),
                **(
                    {
                        "decision_reason": refreeze["reason"],
                        "decided_at": refreeze["decided_at"],
                    } if refreeze else {}
                ),
            })
    ineffective_reset_breakdown.sort(
        key=lambda item: (
            item["after_jitter_event_rate"]
            - item["before_jitter_event_rate"],
            item["after_change_rate"] - item["before_change_rate"],
        ),
        reverse=True,
    )



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
        "manual_overrides": manual_overrides,
        "successful_overrides": successful_overrides,
        "override_success_rate": (
            round(successful_overrides / manual_overrides * 100, 1)
            if manual_overrides else None
        ),
        "risk_warnings": risk_warnings,
        "risk_warning_overrides": risk_warning_overrides,
        "risk_warning_adoption_rate": (
            round(risk_warning_overrides / risk_warnings * 100, 1)
            if risk_warnings else None
        ),
        "risk_warning_recoveries": risk_warning_recoveries,
        "risk_warning_recovery_rate": (
            round(
                risk_warning_recoveries / risk_warning_overrides * 100, 1
            )
            if risk_warning_overrides else None
        ),
        "risk_warning_breakdown": risk_warning_breakdown,
        "risk_level_transitions": risk_level_transitions,
        "risk_level_events": risk_level_events,
        "risk_level_changes": risk_level_changes,
        "risk_level_change_rate": (
            round(risk_level_changes / risk_level_events * 100, 1)
            if risk_level_events else None
        ),
        "risk_level_jitters": risk_level_jitters,
        "risk_level_jitter_rate": (
            round(risk_level_jitters / risk_level_changes * 100, 1)
            if risk_level_changes else None
        ),
        "calibrated_hysteresis_groups": calibrated_hysteresis_groups,
        "risk_calibration_effectiveness": risk_calibration_effectiveness,
        "ineffective_calibration_breakdown": ineffective_calibration_breakdown,
        "hysteresis_rollback_audit": hysteresis_rollback_audit,
        "hysteresis_restoration_audit": hysteresis_restoration_audit,
        "hysteresis_reset_audit": hysteresis_reset_audit,
        "hysteresis_refreeze_audit": hysteresis_refreeze_audit,
        "ineffective_rollback_breakdown": ineffective_rollback_breakdown,
        "ineffective_restoration_breakdown": ineffective_restoration_breakdown,
        "ineffective_reset_breakdown": ineffective_reset_breakdown,
        "override_breakdown": override_breakdown,
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


def _decide_hysteresis_change(
    failure_type, failed_stage, decision, reason, action
):
    if not isinstance(failure_type, str) or not failure_type.strip():
        raise ValueError("failure_type is required.")
    if failed_stage is not None and not isinstance(failed_stage, str):
        raise ValueError("failed_stage must be a string or null.")
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected.")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason is required.")
    reason = reason.strip()
    if len(reason) > MAX_ROLLBACK_REASON_LENGTH:
        raise ValueError(
            f"reason must be at most {MAX_ROLLBACK_REASON_LENGTH} characters."
        )
    if contains_sensitive_memory(reason):
        raise ValueError(SENSITIVE_WORKFLOW_ERROR)

    failure_type = failure_type.strip()
    failed_stage = failed_stage.strip() if failed_stage else None
    if action == "rollback":
        recommendation_key = "ineffective_calibration_breakdown"
        status_key = "rollback_status"
        unavailable_error = "Rollback recommendation unavailable."
    elif action == "restoration":
        recommendation_key = "ineffective_rollback_breakdown"
        status_key = "restoration_status"
        unavailable_error = "Restoration recommendation unavailable."
    elif action == "reset":
        recommendation_key = "ineffective_restoration_breakdown"
        status_key = "reset_status"
        unavailable_error = "Reset recommendation unavailable."
    else:
        recommendation_key = "ineffective_reset_breakdown"
        status_key = "refreeze_status"
        unavailable_error = "Refreeze recommendation unavailable."

    metrics = get_retry_effectiveness()
    cycle_blocked = any(
        item["failure_type"] == failure_type
        and item["failed_stage"] == failed_stage
        and item["cycle_status"] == "blocked"
        for item in metrics["ineffective_restoration_breakdown"]
    )
    if action in {"rollback", "restoration"} and cycle_blocked:
        raise ValueError(
            "Hysteresis strategy cycle blocked pending manual review."
        )

    proposal = next(
        (
            item
            for item in metrics[recommendation_key]
            if item["failure_type"] == failure_type
            and item["failed_stage"] == failed_stage
            and item[status_key] != "completed"
        ),
        None,
    )
    if proposal is None:
        raise ValueError(unavailable_error)

    previous_hysteresis = proposal["current_hysteresis"]
    target_hysteresis = proposal.get(
        "target_hysteresis", previous_hysteresis
    )
    execution_status = (
        "completed" if decision == "approved" else "not_executed"
    )
    result_hysteresis = (
        target_hysteresis if decision == "approved"
        else previous_hysteresis
    )
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        workflow_rowid = conn.execute(
            "SELECT COALESCE(MAX(rowid), 0) FROM workflow_runs"
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO workflow_hysteresis_rollbacks (
                action, failure_type, failed_stage, decision, reason,
                previous_hysteresis, target_hysteresis, execution_status,
                result_hysteresis, workflow_rowid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                failure_type,
                failed_stage,
                decision,
                reason,
                previous_hysteresis,
                target_hysteresis,
                execution_status,
                result_hysteresis,
                workflow_rowid,
            ),
        )
        decided_at = conn.execute(
            """
            SELECT decided_at
            FROM workflow_hysteresis_rollbacks
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()[0]

    return {
        "failure_type": failure_type,
        "failed_stage": failed_stage,
        "decision": decision,
        "reason": reason,
        "previous_hysteresis": previous_hysteresis,
        "target_hysteresis": target_hysteresis,
        "execution_status": execution_status,
        "result_hysteresis": result_hysteresis,
        "decided_at": decided_at,
    }

def decide_hysteresis_rollback(
    failure_type, failed_stage, decision, reason
):
    return _decide_hysteresis_change(
        failure_type, failed_stage, decision, reason, "rollback"
    )


def decide_hysteresis_refreeze(
    failure_type, failed_stage, decision, reason
):
    return _decide_hysteresis_change(
        failure_type, failed_stage, decision, reason, "refreeze"
    )


def decide_hysteresis_restoration(
    failure_type, failed_stage, decision, reason
):
    return _decide_hysteresis_change(
        failure_type, failed_stage, decision, reason, "restoration"
    )


def decide_hysteresis_reset(
    failure_type, failed_stage, decision, reason
):
    return _decide_hysteresis_change(
        failure_type, failed_stage, decision, reason, "reset"
    )



def get_workflow_run(workflow_id):
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty.")

    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        row = conn.execute(
            """
            SELECT workflow_id, workflow_type, objective, context, status,
                   steps_json, final_output, error, retry_of, attempt_number,
                   override_source, override_reason, created_at
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
            SELECT workflow_id, status, attempt_number, steps_json,
                   override_source, override_reason
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
        attempt_data = {
            "workflow_id": attempt[0],
            "status": attempt[1],
            "attempt_number": attempt[2],
            **_workflow_diagnostics(attempt_steps),
        }
        if attempt[4]:
            attempt_data.update({
                "override_source": attempt[4],
                "override_reason": attempt[5],
            })
        attempts.append(attempt_data)

    diagnostics = _workflow_diagnostics(steps)
    decision = _failure_decision(
        row[4], diagnostics["failed_stage"], row[7]
    )
    retry_metrics = (
        get_retry_effectiveness() if decision["retry_recommended"] else None
    )
    feedback = (
        next((
            item
            for item in retry_metrics["decision_breakdown"]
            if item["failure_type"] == decision["failure_type"]
            and item["failed_stage"] == diagnostics["failed_stage"]
        ), None)
        if decision["retry_recommended"]
        else None
    )
    decision.update({
        "policy_adjusted": False,
        "historical_hit_rate": feedback["hit_rate"] if feedback else None,
        "historical_sample_size": feedback["accepted"] if feedback else 0,
        "historical_override_success_rate": None,
        "historical_override_sample_size": 0,
        "override_risk_warning": None,
        "override_risk_level": None,
    })
    if (
        feedback
        and feedback["sample_sufficient"]
        and feedback["hit_rate"] < MIN_RETRY_HIT_RATE
    ):
        decision.update({
            "retry_recommended": False,
            "policy_adjusted": True,
            "recommended_action": (
                f"历史重跑命中率仅 {feedback['hit_rate']}%"
                f"（{feedback['hits']}/{feedback['accepted']}），"
                "不建议继续重跑；先检查失败详情。"
            ),
        })

    override_feedback = (
        next((
            item
            for item in retry_metrics["override_breakdown"]
            if item["failure_type"] == decision["failure_type"]
            and item["failed_stage"] == diagnostics["failed_stage"]
        ), None)
        if decision["policy_adjusted"]
        else None
    )
    if override_feedback:
        decision.update({
            "historical_override_success_rate": (
                override_feedback["success_rate"]
            ),
            "historical_override_sample_size": (
                override_feedback["overrides"]
            ),
        })
        if (
            override_feedback["sample_sufficient"]
            and override_feedback["success_rate"] < MIN_RETRY_HIT_RATE
        ):
            decision["override_risk_level"] = "medium"
            decision["override_risk_warning"] = (
                f"历史人工覆盖成功率仅 {override_feedback['success_rate']}%"
                f"（{override_feedback['successful']}/{override_feedback['overrides']}），"
                "风险较高；仍可由人工决定是否继续。"
            )

    warning_feedback = (
        next((
            item
            for item in retry_metrics["risk_warning_breakdown"]
            if item["failure_type"] == decision["failure_type"]
            and item["failed_stage"] == diagnostics["failed_stage"]
        ), None)
        if decision["override_risk_level"]
        else None
    )
    if warning_feedback and warning_feedback["risk_level"] == "high":
        decision.update({
            "override_risk_level": "high",
            "override_risk_warning": (
                f"高风险：该组风险提示后仍有 {warning_feedback['adoption_rate']}% "
                f"继续人工覆盖（{warning_feedback['overrides']}/"
                f"{warning_feedback['warnings']}），覆盖后恢复率仅 "
                f"{warning_feedback['recovery_rate']}%"
                f"（{warning_feedback['recoveries']}/"
                f"{warning_feedback['overrides']}）；仍可由人工决定是否继续。"
            ),
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
        "override_source": row[10],
        "override_reason": row[11],
        "final_output": row[6],
        "error": row[7],
        **diagnostics,
        **decision,
        "created_at": row[12],
    }
