import importlib.util
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import replace

module_spec = importlib.util.find_spec("workflow_history")
assert module_spec is not None, "workflow_history.py 尚未实现"

import workflow_history
from task_contract import AgentResult
from workflow_contract import WorkflowResult


original_db_path = workflow_history.DB_PATH
landing_page_files = {
    "index.html": "<main>Stored</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}

with tempfile.TemporaryDirectory() as temp_dir:
    workflow_history.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        with closing(sqlite3.connect(workflow_history.DB_PATH)) as conn:
            conn.execute(
                """
                CREATE TABLE workflow_runs (
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
        workflow_history.init_workflow_history_db()
        with closing(sqlite3.connect(workflow_history.DB_PATH)) as conn:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(workflow_runs)")
            }
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert {"retry_of", "attempt_number", "override_source", "override_reason"} <= columns
        assert "workflow_hysteresis_rollbacks" in tables

        completed = WorkflowResult(
            workflow_id="workflow-completed",
            workflow_type="client_project",
            status="completed",
            steps=[
                AgentResult("task-research", "Search Agent", "completed", "Research 完成"),
                AgentResult("task-strategy", "Strategy Agent", "completed", "Strategy 完成"),
                AgentResult(
                    "task-coding",
                    "Coding Agent",
                    "completed",
                    json.dumps(landing_page_files),
                ),
                AgentResult("task-project", "Client Project Manager Agent", "completed", "项目计划完成"),
            ],
            final_output="项目计划完成",
        )
        completed.steps[0].duration_ms = 12.5

        workflow_history.save_workflow_run("启动餐厅项目", "吉隆坡本地餐厅", completed)

        stored = workflow_history.get_workflow_run("workflow-completed")
        assert stored["objective"] == "启动餐厅项目"
        assert stored["context"] == "吉隆坡本地餐厅"
        assert stored["status"] == "completed"
        assert stored["final_output"] == "项目计划完成"
        assert [step["agent_name"] for step in stored["steps"]] == [
            "Search Agent", "Strategy Agent", "Coding Agent",
            "Client Project Manager Agent",
        ]
        assert stored["landing_page"] == {
            "files": landing_page_files,
        }
        assert stored["duration_ms"] == 12.5
        assert stored["failed_stage"] is None
        assert stored["failure_type"] is None
        assert stored["retry_recommended"] is False
        assert stored["recommended_action"] is None
        assert stored["retry_of"] is None
        assert stored["attempt_number"] == 1

        failed = WorkflowResult(
            workflow_id="workflow-failed",
            workflow_type="client_project",
            status="failed",
            steps=[AgentResult("task-research-failed", "Search Agent", "failed", "", "search unavailable")],
            final_output="",
            error="Search Agent: search unavailable",
        )
        failed.steps[0].duration_ms = 8.5
        workflow_history.save_workflow_run("失败项目", "测试背景", failed)

        stored_failed = workflow_history.get_workflow_run("workflow-failed")
        assert stored_failed["status"] == "failed"
        assert len(stored_failed["steps"]) == 1
        assert stored_failed["error"] == "Search Agent: search unavailable"
        assert stored_failed["landing_page"] is None

        assert stored_failed["duration_ms"] == 8.5
        assert stored_failed["failed_stage"] == "Search Agent"
        assert stored_failed["failure_type"] == "transient"
        assert stored_failed["retry_recommended"] is True
        assert stored_failed["recommended_action"] == "建议重跑：临时故障通常可恢复。"
        recent = workflow_history.get_workflow_history(limit=1)
        assert len(recent) == 1
        assert recent[0]["workflow_id"] == "workflow-failed"
        assert recent[0]["retry_of"] is None
        assert recent[0]["attempt_number"] == 1
        assert workflow_history.get_workflow_run("missing") is None

        assert workflow_history.get_next_attempt_number("workflow-failed") == 2
        assert workflow_history.get_retry_effectiveness() == {
            "retry_chains": 0,
            "recovered_chains": 0,
            "recovery_rate": None,
            "duration_samples": 0,
            "average_duration_change_ms": None,
            "top_failed_stage": None,
            "retry_recommendations": 1,
            "accepted_recommendations": 0,
            "recommendation_adoption_rate": 0.0,
            "recommendation_hits": 0,
            "decision_hit_rate": None,
            "minimum_decision_samples": 3,
            "manual_overrides": 0,
            "successful_overrides": 0,
            "override_success_rate": None,
            "risk_warnings": 0,
            "risk_warning_overrides": 0,
            "risk_warning_adoption_rate": None,
            "risk_warning_recoveries": 0,
            "risk_warning_recovery_rate": None,
            "risk_warning_breakdown": [],
            "risk_level_transitions": [],
            "risk_level_events": 0,
            "risk_level_changes": 0,
            "risk_level_change_rate": None,
            "risk_level_jitters": 0,
            "risk_level_jitter_rate": None,
            "calibrated_hysteresis_groups": 0,
            "risk_calibration_effectiveness": None,
            "ineffective_calibration_breakdown": [],
            "hysteresis_rollback_audit": [],
            "ineffective_rollback_breakdown": [],
            "override_breakdown": [],
            "decision_breakdown": [{
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "recommendations": 1,
                "accepted": 0,
                "hits": 0,
                "hit_rate": None,
                "sample_sufficient": False,
            }],
        }
        failure_cases = (
            (
                "workflow-invalid-output",
                "Coding Agent",
                "Coding Agent 必须返回有效 JSON。",
                "validation",
                False,
                "先修正输出格式，再执行。",
            ),
            (
                "workflow-permission",
                "QA Agent",
                "Permission denied",
                "configuration",
                False,
                "先修复配置或权限，再执行。",
            ),
            (
                "workflow-search-provider",
                "Search Agent",
                "Provider rejected request",
                "external_dependency",
                True,
                "建议重跑：Search Agent 外部依赖可能恢复。",
            ),
            (
                "workflow-execution",
                "Coding Agent",
                "Unexpected response",
                "execution",
                False,
                "先检查失败详情，再决定是否重跑。",
            ),
        )
        for (
            workflow_id, stage, error, failure_type, retry_recommended, action
        ) in failure_cases:
            case = WorkflowResult(
                workflow_id=workflow_id,
                workflow_type="client_project",
                status="failed",
                steps=[AgentResult(
                    f"task-{workflow_id}", stage, "failed", "", error
                )],
                final_output="",
                error=f"{stage}: {error}",
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", case
            )
            stored_case = workflow_history.get_workflow_run(workflow_id)
            assert stored_case["failure_type"] == failure_type
            assert stored_case["retry_recommended"] is retry_recommended
            assert stored_case["recommended_action"] == action

        retry = WorkflowResult(
            workflow_id="workflow-retry-2",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult(
                "task-retry", "Search Agent", "completed", "重跑完成"
            )],
            final_output="重跑完成",
            retry_of="workflow-failed",
            attempt_number=2,
        )
        retry.steps[0].duration_ms = 5.0
        workflow_history.save_workflow_run("失败项目", "测试背景", retry)

        stored_retry = workflow_history.get_workflow_run("workflow-retry-2")
        assert stored_retry["retry_of"] == "workflow-failed"
        expected_attempts = [
            {
                "workflow_id": "workflow-failed",
                "status": "failed",
                "attempt_number": 1,
                "duration_ms": 8.5,
                "failed_stage": "Search Agent",
            },
            {
                "workflow_id": "workflow-retry-2",
                "status": "completed",
                "attempt_number": 2,
                "duration_ms": 5.0,
                "failed_stage": None,
            },
        ]
        assert stored_retry["attempts"] == expected_attempts
        assert workflow_history.get_workflow_run(
            "workflow-failed"
        )["attempts"] == expected_attempts
        assert stored_retry["attempt_number"] == 2
        assert workflow_history.get_next_attempt_number("workflow-failed") == 3
        assert workflow_history.get_retry_effectiveness() == {
            "retry_chains": 1,
            "recovered_chains": 1,
            "recovery_rate": 100.0,
            "duration_samples": 1,
            "average_duration_change_ms": -3.5,
            "top_failed_stage": "Search Agent",
            "retry_recommendations": 2,
            "accepted_recommendations": 1,
            "recommendation_adoption_rate": 50.0,
            "recommendation_hits": 1,
            "decision_hit_rate": 100.0,
            "minimum_decision_samples": 3,
            "manual_overrides": 0,
            "successful_overrides": 0,
            "override_success_rate": None,
            "risk_warnings": 0,
            "risk_warning_overrides": 0,
            "risk_warning_adoption_rate": None,
            "risk_warning_recoveries": 0,
            "risk_warning_recovery_rate": None,
            "risk_warning_breakdown": [],
            "risk_level_transitions": [],
            "risk_level_events": 0,
            "risk_level_changes": 0,
            "risk_level_change_rate": None,
            "risk_level_jitters": 0,
            "risk_level_jitter_rate": None,
            "calibrated_hysteresis_groups": 0,
            "risk_calibration_effectiveness": None,
            "ineffective_calibration_breakdown": [],
            "hysteresis_rollback_audit": [],
            "ineffective_rollback_breakdown": [],
            "override_breakdown": [],
            "decision_breakdown": [
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "recommendations": 1,
                    "accepted": 1,
                    "hits": 1,
                    "hit_rate": 100.0,
                    "sample_sufficient": False,
                },
                {
                    "failure_type": "external_dependency",
                    "failed_stage": "Search Agent",
                    "recommendations": 1,
                    "accepted": 0,
                    "hits": 0,
                    "hit_rate": None,
                    "sample_sufficient": False,
                },
            ],
        }

        missed_retry = WorkflowResult(
            workflow_id="workflow-search-provider-retry",
            workflow_type="client_project",
            status="failed",
            steps=[AgentResult(
                "task-search-retry", "Search Agent", "failed", "",
                "Provider unavailable",
            )],
            final_output="",
            error="Search Agent: Provider unavailable",
            retry_of="workflow-search-provider",
            attempt_number=2,
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", missed_retry
        )

        with closing(sqlite3.connect(workflow_history.DB_PATH)) as conn, conn:
            conn.execute(
                "UPDATE workflow_runs SET steps_json = ? WHERE workflow_id = ?",
                (
                    json.dumps([{
                        "task_id": "task-research-failed",
                        "agent_name": "Search Agent",
                        "status": "failed",
                        "output": "",
                        "error": "search unavailable",
                    }]),
                    "workflow-failed",
                ),
            )
        assert workflow_history.get_retry_effectiveness() == {
            "retry_chains": 2,
            "recovered_chains": 1,
            "recovery_rate": 50.0,
            "duration_samples": 1,
            "average_duration_change_ms": 0.0,
            "top_failed_stage": "Search Agent",
            "retry_recommendations": 3,
            "accepted_recommendations": 2,
            "recommendation_adoption_rate": 66.7,
            "recommendation_hits": 1,
            "decision_hit_rate": 50.0,
            "minimum_decision_samples": 3,
            "manual_overrides": 0,
            "successful_overrides": 0,
            "override_success_rate": None,
            "risk_warnings": 0,
            "risk_warning_overrides": 0,
            "risk_warning_adoption_rate": None,
            "risk_warning_recoveries": 0,
            "risk_warning_recovery_rate": None,
            "risk_warning_breakdown": [],
            "risk_level_transitions": [],
            "risk_level_events": 0,
            "risk_level_changes": 0,
            "risk_level_change_rate": None,
            "risk_level_jitters": 0,
            "risk_level_jitter_rate": None,
            "calibrated_hysteresis_groups": 0,
            "risk_calibration_effectiveness": None,
            "ineffective_calibration_breakdown": [],
            "hysteresis_rollback_audit": [],
            "ineffective_rollback_breakdown": [],
            "override_breakdown": [],
            "decision_breakdown": [
                {
                    "failure_type": "external_dependency",
                    "failed_stage": "Search Agent",
                    "recommendations": 1,
                    "accepted": 1,
                    "hits": 0,
                    "hit_rate": 0.0,
                    "sample_sufficient": False,
                },
                {
                    "failure_type": "transient",
                    "failed_stage": "Search Agent",
                    "recommendations": 2,
                    "accepted": 1,
                    "hits": 1,
                    "hit_rate": 100.0,
                    "sample_sufficient": False,
                },
            ],
        }

        for (
            suffix, retry_status, expected_accepted, expected_sufficient
        ) in (
            ("2", "failed", 2, False),
            ("3", "completed", 3, True),
        ):
            root_id = f"workflow-provider-{suffix}"
            provider_failure = WorkflowResult(
                workflow_id=root_id,
                workflow_type="client_project",
                status="failed",
                steps=[AgentResult(
                    f"task-provider-{suffix}", "Search Agent", "failed", "",
                    "Provider rejected request",
                )],
                final_output="",
                error="Search Agent: Provider rejected request",
            )
            retry_error = (
                "Provider rejected request"
                if retry_status == "failed"
                else None
            )
            provider_retry = WorkflowResult(
                workflow_id=f"{root_id}-retry",
                workflow_type="client_project",
                status=retry_status,
                steps=[AgentResult(
                    f"task-provider-retry-{suffix}", "Search Agent",
                    retry_status,
                    "Recovered" if retry_status == "completed" else "",
                    retry_error,
                )],
                final_output=(
                    "Recovered" if retry_status == "completed" else ""
                ),
                error=(
                    f"Search Agent: {retry_error}" if retry_error else None
                ),
                retry_of=root_id,
                attempt_number=2,
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", provider_failure
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", provider_retry
            )
            breakdown = next(
                item
                for item in workflow_history.get_retry_effectiveness()[
                    "decision_breakdown"
                ]
                if item["failure_type"] == "external_dependency"
            )
            assert breakdown["accepted"] == expected_accepted
            assert breakdown["sample_sufficient"] is expected_sufficient

        downgraded = workflow_history.get_workflow_run(
            "workflow-provider-3"
        )
        assert downgraded["failure_type"] == "external_dependency"
        assert downgraded["retry_recommended"] is False
        assert downgraded["policy_adjusted"] is True
        assert downgraded["historical_hit_rate"] == 33.3
        assert downgraded["historical_sample_size"] == 3
        assert downgraded["recommended_action"] == (
            "历史重跑命中率仅 33.3%（1/3），"
            "不建议继续重跑；先检查失败详情。"
        )
        baseline_external = next(
            item for item in workflow_history.get_retry_effectiveness()["decision_breakdown"]
            if item["failure_type"] == "external_dependency"
        )

        override_root = WorkflowResult(
            workflow_id="workflow-provider-override",
            workflow_type="client_project",
            status="failed",
            steps=[AgentResult(
                "task-provider-override", "Search Agent", "failed", "",
                "Provider rejected request",
            )],
            final_output="",
            error="Search Agent: Provider rejected request",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", override_root
        )
        assert workflow_history.get_workflow_run(
            override_root.workflow_id
        )["policy_adjusted"] is True

        manual_retry = WorkflowResult(
            workflow_id="workflow-provider-override-retry",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult(
                "task-provider-override-retry", "Search Agent",
                "completed", "Recovered",
            )],
            final_output="Recovered",
            retry_of=override_root.workflow_id,
            attempt_number=2,
            override_source=override_root.workflow_id,
            override_reason="供应商已人工确认恢复",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", manual_retry
        )
        audited_retry = workflow_history.get_workflow_run(
            manual_retry.workflow_id
        )
        assert audited_retry["override_source"] == override_root.workflow_id
        assert audited_retry["override_reason"] == "供应商已人工确认恢复"
        assert audited_retry["attempts"][-1]["override_source"] == (
            override_root.workflow_id
        )
        metrics = workflow_history.get_retry_effectiveness()
        assert metrics["manual_overrides"] == 1
        assert metrics["successful_overrides"] == 1
        assert metrics["override_success_rate"] == 100.0
        external_metrics = next(
            item for item in metrics["decision_breakdown"]
            if item["failure_type"] == "external_dependency"
        )
        assert external_metrics["recommendations"] == baseline_external["recommendations"]
        assert external_metrics["accepted"] == 3
        assert external_metrics["hits"] == 1
        assert external_metrics["hit_rate"] == 33.3
        assert metrics["override_breakdown"] == [{
            "failure_type": "external_dependency",
            "failed_stage": "Search Agent",
            "overrides": 1,
            "successful": 1,
            "success_rate": 100.0,
            "sample_sufficient": False,
        }]
        low_sample = workflow_history.get_workflow_run("workflow-failed")
        assert low_sample["retry_recommended"] is True
        assert low_sample["policy_adjusted"] is False
        assert low_sample["historical_hit_rate"] == 100.0
        assert low_sample["historical_sample_size"] == 1
        for suffix in ("2", "3"):
            transient_root_id = f"workflow-transient-{suffix}"
            transient_root = replace(
                failed, workflow_id=transient_root_id,
                retry_of=None, attempt_number=1,
            )
            transient_retry = replace(
                failed,
                workflow_id=f"{transient_root_id}-retry",
                retry_of=transient_root_id,
                attempt_number=2,
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", transient_root
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", transient_retry
            )

        transient_override_root = replace(
            failed,
            workflow_id="workflow-transient-override",
            retry_of=None,
            attempt_number=1,
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", transient_override_root
        )
        transient_decision = workflow_history.get_workflow_run(
            transient_override_root.workflow_id
        )
        assert transient_decision["policy_adjusted"] is True
        assert transient_decision["historical_hit_rate"] == 33.3

        override_source = transient_override_root.workflow_id
        for attempt_number in range(2, 5):
            failed_override = replace(
                failed,
                workflow_id=f"workflow-transient-override-{attempt_number}",
                retry_of=transient_override_root.workflow_id,
                attempt_number=attempt_number,
                override_source=override_source,
                override_reason="人工确认后继续尝试",
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", failed_override
            )
            override_source = failed_override.workflow_id

        metrics = workflow_history.get_retry_effectiveness()
        assert metrics["manual_overrides"] == 4
        assert metrics["successful_overrides"] == 1
        assert metrics["override_success_rate"] == 25.0
        assert metrics["override_breakdown"] == [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "overrides": 3,
                "successful": 0,
                "success_rate": 0.0,
                "sample_sufficient": True,
            },
            {
                "failure_type": "external_dependency",
                "failed_stage": "Search Agent",
                "overrides": 1,
                "successful": 1,
                "success_rate": 100.0,
                "sample_sufficient": False,
            },
        ]

        risky_override = workflow_history.get_workflow_run(
            transient_override_root.workflow_id
        )
        assert risky_override["historical_override_success_rate"] == 0.0
        assert risky_override["historical_override_sample_size"] == 3
        assert risky_override["override_risk_warning"] == (
            "历史人工覆盖成功率仅 0.0%（0/3），"
            "风险较高；仍可由人工决定是否继续。"
        )
        low_sample_override = workflow_history.get_workflow_run(
            override_root.workflow_id
        )
        assert low_sample_override["historical_override_success_rate"] == 100.0
        assert low_sample_override["historical_override_sample_size"] == 1
        assert low_sample_override["override_risk_warning"] is None

        assert metrics["risk_warnings"] == 1
        assert metrics["risk_warning_overrides"] == 0
        assert metrics["risk_warning_adoption_rate"] == 0.0
        assert metrics["risk_warning_recoveries"] == 0
        assert metrics["risk_warning_recovery_rate"] is None

        recovered_risky_override = replace(
            manual_retry,
            workflow_id="workflow-transient-override-5",
            retry_of=transient_override_root.workflow_id,
            attempt_number=5,
            override_source="workflow-transient-override-4",
            override_reason="已知风险后仍决定继续",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", recovered_risky_override
        )
        open_risk = replace(
            failed,
            workflow_id="workflow-transient-risk-open",
            retry_of=None,
            attempt_number=1,
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", open_risk
        )
        risk_metrics = workflow_history.get_retry_effectiveness()
        assert risk_metrics["risk_warnings"] == 2
        assert risk_metrics["risk_warning_overrides"] == 1
        assert risk_metrics["risk_warning_adoption_rate"] == 50.0
        assert risk_metrics["risk_warning_recoveries"] == 1
        assert risk_metrics["risk_warning_recovery_rate"] == 100.0

        second_open_risk = replace(
            open_risk, workflow_id="workflow-transient-risk-open-2"
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", second_open_risk
        )
        external_risk_root = replace(
            override_root, workflow_id="workflow-provider-risk"
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", external_risk_root
        )
        external_override_source = external_risk_root.workflow_id
        for attempt_number in range(2, 4):
            failed_external_override = replace(
                override_root,
                workflow_id=f"workflow-provider-risk-{attempt_number}",
                retry_of=external_risk_root.workflow_id,
                attempt_number=attempt_number,
                override_source=external_override_source,
                override_reason="人工确认供应商状态后继续",
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", failed_external_override
            )
            external_override_source = failed_external_override.workflow_id

        segmented_metrics = workflow_history.get_retry_effectiveness()
        assert segmented_metrics["risk_warning_breakdown"] == [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "warnings": 3,
                "overrides": 1,
                "adoption_rate": 33.3,
                "recoveries": 1,
                "recovery_rate": 100.0,
                "sample_sufficient": True,
                "risk_level": "medium",
                "risk_events": 4,
                "level_changes": 0,
                "change_rate": 0.0,
                "jitters": 0,
                "jitter_rate": None,
                "hysteresis": 10.0,
                "hysteresis_calibrated": False,
                "calibration_effectiveness": None,
            },
            {
                "failure_type": "external_dependency",
                "failed_stage": "Search Agent",
                "warnings": 1,
                "overrides": 0,
                "adoption_rate": 0.0,
                "recoveries": 0,
                "recovery_rate": None,
                "sample_sufficient": False,
                "risk_level": "medium",
                "risk_events": 1,
                "level_changes": 0,
                "change_rate": 0.0,
                "jitters": 0,
                "jitter_rate": None,
                "hysteresis": 10.0,
                "hysteresis_calibrated": False,
                "calibration_effectiveness": None,
            },
        ]

        medium_risk = workflow_history.get_workflow_run(open_risk.workflow_id)
        assert medium_risk["override_risk_level"] == "medium"

        for source in (open_risk, second_open_risk):
            failed_risk_override = replace(
                failed,
                workflow_id=f"{source.workflow_id}-override",
                retry_of=source.workflow_id,
                attempt_number=2,
                override_source=source.workflow_id,
                override_reason="已知风险后仍决定继续",
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", failed_risk_override
            )

        high_risk = workflow_history.get_workflow_run(
            second_open_risk.workflow_id
        )
        assert high_risk["override_risk_level"] == "high"
        assert high_risk["override_risk_warning"] == (
            "高风险：该组风险提示后仍有 60.0% 继续人工覆盖（3/5），"
            "覆盖后恢复率仅 33.3%（1/3）；仍可由人工决定是否继续。"
        )

        stable_risk = None
        for suffix in ("stable-1", "stable-2"):
            stable_risk = replace(
                failed,
                workflow_id=f"workflow-transient-risk-{suffix}",
                retry_of=None,
                attempt_number=1,
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", stable_risk
            )
        assert workflow_history.get_workflow_run(
            stable_risk.workflow_id
        )["override_risk_level"] == "high"

        downgraded_risk = replace(
            failed,
            workflow_id="workflow-transient-risk-downgraded",
            retry_of=None,
            attempt_number=1,
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", downgraded_risk
        )
        assert workflow_history.get_workflow_run(
            downgraded_risk.workflow_id
        )["override_risk_level"] == "medium"
        assert workflow_history.get_retry_effectiveness()[
            "risk_level_transitions"
        ] == [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "from_level": "medium",
                "to_level": "high",
                "workflow_id": "workflow-transient-risk-open-2-override",
                "warnings": 4,
                "overrides": 3,
                "adoption_rate": 75.0,
                "recoveries": 1,
                "recovery_rate": 33.3,
            },
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "from_level": "high",
                "to_level": "medium",
                "workflow_id": downgraded_risk.workflow_id,
                "warnings": 8,
                "overrides": 3,
                "adoption_rate": 37.5,
                "recoveries": 1,
                "recovery_rate": 33.3,
            },
        ]

        jitter_override = replace(
            failed,
            workflow_id="workflow-transient-risk-jitter-override",
            retry_of=downgraded_risk.workflow_id,
            attempt_number=2,
            override_source=downgraded_risk.workflow_id,
            override_reason="按人工判断继续验证",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", jitter_override
        )
        assert workflow_history.get_workflow_run(
            downgraded_risk.workflow_id
        )["override_risk_level"] == "high"

        calibrated_risk = None
        for suffix in ("calibrated-1", "calibrated-2"):
            calibrated_risk = replace(
                failed,
                workflow_id=f"workflow-transient-risk-{suffix}",
                retry_of=None,
                attempt_number=1,
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", calibrated_risk
            )
        assert workflow_history.get_workflow_run(
            calibrated_risk.workflow_id
        )["override_risk_level"] == "high"

        calibrated_exit = replace(
            failed,
            workflow_id="workflow-transient-risk-calibrated-exit",
            retry_of=None,
            attempt_number=1,
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", calibrated_exit
        )
        assert workflow_history.get_workflow_run(
            calibrated_exit.workflow_id
        )["override_risk_level"] == "medium"

        stability_metrics = workflow_history.get_retry_effectiveness()
        assert {
            key: stability_metrics[key]
            for key in (
                "risk_level_events",
                "risk_level_changes",
                "risk_level_change_rate",
                "risk_level_jitters",
                "risk_level_jitter_rate",
                "calibrated_hysteresis_groups",
            )
        } == {
            "risk_level_events": 17,
            "risk_level_changes": 4,
            "risk_level_change_rate": 23.5,
            "risk_level_jitters": 1,
            "risk_level_jitter_rate": 25.0,
            "calibrated_hysteresis_groups": 1,
        }
        transient_stability = next(
            item
            for item in stability_metrics["risk_warning_breakdown"]
            if item["failure_type"] == "transient"
        )
        assert {
            key: transient_stability[key]
            for key in (
                "risk_events",
                "level_changes",
                "change_rate",
                "jitters",
                "jitter_rate",
                "hysteresis",
                "hysteresis_calibrated",
            )
        } == {
            "risk_events": 16,
            "level_changes": 4,
            "change_rate": 25.0,
            "jitters": 1,
            "jitter_rate": 25.0,
            "hysteresis": 15.0,
            "hysteresis_calibrated": True,
        }
        calibration_effectiveness = {
            "before": {
                "events": 12,
                "changes": 3,
                "change_rate": 25.0,
                "jitters": 1,
                "jitter_event_rate": 8.3,
            },
            "after": {
                "events": 4,
                "changes": 1,
                "change_rate": 25.0,
                "jitters": 0,
                "jitter_event_rate": 0.0,
            },
            "sample_sufficient": True,
            "effective": True,
        }
        assert stability_metrics[
            "risk_calibration_effectiveness"
        ] == calibration_effectiveness
        assert transient_stability[
            "calibration_effectiveness"
        ] == calibration_effectiveness

        successful_post_calibration = replace(
            completed,
            workflow_id="workflow-transient-risk-post-calibration-success",
            retry_of="workflow-transient-risk-calibrated-1",
            attempt_number=2,
            override_source="workflow-transient-risk-calibrated-1",
            override_reason="验证校准后成功覆盖",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", successful_post_calibration
        )
        failed_post_calibration = replace(
            failed,
            workflow_id="workflow-transient-risk-post-calibration-failure",
            retry_of="workflow-transient-risk-calibrated-2",
            attempt_number=2,
            override_source="workflow-transient-risk-calibrated-2",
            override_reason="验证校准后失败覆盖",
        )
        workflow_history.save_workflow_run(
            "分类测试", "测试背景", failed_post_calibration
        )

        ineffective_metrics = workflow_history.get_retry_effectiveness()
        ineffective_group = next(
            item
            for item in ineffective_metrics["risk_warning_breakdown"]
            if item["failure_type"] == "transient"
        )
        ineffective_effectiveness = {
            "before": {
                "events": 12,
                "changes": 3,
                "change_rate": 25.0,
                "jitters": 1,
                "jitter_event_rate": 8.3,
            },
            "after": {
                "events": 7,
                "changes": 2,
                "change_rate": 28.6,
                "jitters": 1,
                "jitter_event_rate": 14.3,
            },
            "sample_sufficient": True,
            "effective": False,
        }
        assert ineffective_group[
            "calibration_effectiveness"
        ] == ineffective_effectiveness
        assert ineffective_metrics[
            "risk_calibration_effectiveness"
        ] == ineffective_effectiveness
        assert ineffective_group["hysteresis"] == 15.0
        assert ineffective_metrics["ineffective_calibration_breakdown"] == [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "current_hysteresis": 15.0,
                "target_hysteresis": 10.0,
                "post_calibration_events": 7,
                "before_change_rate": 25.0,
                "after_change_rate": 28.6,
                "before_jitter_event_rate": 8.3,
                "after_jitter_event_rate": 14.3,
                "rollback_status": "approval_required",
            }
        ]

        rejected_rollback = workflow_history.decide_hysteresis_rollback(
            "transient",
            "Search Agent",
            "rejected",
            "证据不足，暂时保留当前滞回值",
        )
        assert {
            key: value
            for key, value in rejected_rollback.items()
            if key != "decided_at"
        } == {
            "failure_type": "transient",
            "failed_stage": "Search Agent",
            "decision": "rejected",
            "reason": "证据不足，暂时保留当前滞回值",
            "previous_hysteresis": 15.0,
            "target_hysteresis": 10.0,
            "execution_status": "not_executed",
            "result_hysteresis": 15.0,
        }
        assert rejected_rollback["decided_at"]
        rejected_metrics = workflow_history.get_retry_effectiveness()
        rejected_group = next(
            item
            for item in rejected_metrics["risk_warning_breakdown"]
            if item["failure_type"] == "transient"
        )
        assert rejected_group["hysteresis"] == 15.0
        assert rejected_metrics[
            "ineffective_calibration_breakdown"
        ][0]["rollback_status"] == "rejected"

        approved_rollback = workflow_history.decide_hysteresis_rollback(
            "transient",
            "Search Agent",
            "approved",
            "校准无效，批准回退至基线",
        )
        assert {
            key: value
            for key, value in approved_rollback.items()
            if key != "decided_at"
        } == {
            "failure_type": "transient",
            "failed_stage": "Search Agent",
            "decision": "approved",
            "reason": "校准无效，批准回退至基线",
            "previous_hysteresis": 15.0,
            "target_hysteresis": 10.0,
            "execution_status": "completed",
            "result_hysteresis": 10.0,
        }
        assert approved_rollback["decided_at"]
        approved_metrics = workflow_history.get_retry_effectiveness()
        approved_group = next(
            item
            for item in approved_metrics["risk_warning_breakdown"]
            if item["failure_type"] == "transient"
        )
        assert approved_group["hysteresis"] == 10.0
        approved_proposal = approved_metrics[
            "ineffective_calibration_breakdown"
        ][0]
        assert approved_proposal["rollback_status"] == "completed"
        assert approved_proposal["decision_reason"] == (
            "校准无效，批准回退至基线"
        )
        assert [
            item["decision"]
            for item in approved_metrics["hysteresis_rollback_audit"]
        ] == ["approved", "rejected"]

        pending_rollback_effect = {
            "before": {
                "events": 7,
                "changes": 2,
                "change_rate": 28.6,
                "jitters": 1,
                "jitter_event_rate": 14.3,
            },
            "after": {
                "events": 0,
                "changes": 0,
                "change_rate": None,
                "jitters": 0,
                "jitter_event_rate": None,
            },
            "sample_sufficient": False,
            "effective": None,
        }
        assert approved_metrics["hysteresis_rollback_audit"][0][
            "effectiveness"
        ] == pending_rollback_effect
        assert approved_proposal[
            "rollback_effectiveness"
        ] == pending_rollback_effect

        for index in range(1, 4):
            post_rollback_risk = replace(
                failed,
                workflow_id=f"workflow-transient-post-rollback-{index}",
                retry_of=None,
                attempt_number=1,
            )
            workflow_history.save_workflow_run(
                "分类测试", "测试背景", post_rollback_risk
            )

        post_rollback_metrics = workflow_history.get_retry_effectiveness()
        rollback_effectiveness = {
            "before": {
                "events": 7,
                "changes": 2,
                "change_rate": 28.6,
                "jitters": 1,
                "jitter_event_rate": 14.3,
            },
            "after": {
                "events": 3,
                "changes": 1,
                "change_rate": 33.3,
                "jitters": 0,
                "jitter_event_rate": 0.0,
            },
            "sample_sufficient": True,
            "effective": False,
        }
        assert post_rollback_metrics["hysteresis_rollback_audit"][0][
            "effectiveness"
        ] == rollback_effectiveness
        assert post_rollback_metrics[
            "ineffective_calibration_breakdown"
        ][0]["rollback_effectiveness"] == rollback_effectiveness

        assert post_rollback_metrics[
            "ineffective_rollback_breakdown"
        ] == [
            {
                "failure_type": "transient",
                "failed_stage": "Search Agent",
                "current_hysteresis": 10.0,
                "target_hysteresis": 15.0,
                "post_rollback_events": 3,
                "before_change_rate": 28.6,
                "after_change_rate": 33.3,
                "before_jitter_event_rate": 14.3,
                "after_jitter_event_rate": 0.0,
                "restoration_status": "approval_required",
            }
        ]
        assert approved_group["hysteresis"] == 10.0


        try:
            workflow_history.get_workflow_history(limit=0)
        except ValueError:
            pass
        else:
            raise AssertionError("非正数 limit 必须被拒绝")

        try:
            workflow_history.get_workflow_run(" ")
        except ValueError:
            pass
        else:
            raise AssertionError("空 workflow_id 必须被拒绝")

        try:
            workflow_history.save_workflow_run("重复项目", "重复背景", completed)
        except RuntimeError:
            pass
        else:
            raise AssertionError("重复 workflow_id 必须失败")

        sensitive = WorkflowResult(
            workflow_id="workflow-sensitive",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult("task-sensitive", "Search Agent", "completed", "API Key: secret")],
            final_output="敏感输出",
        )
        try:
            workflow_history.save_workflow_run("敏感项目", "测试背景", sensitive)
        except ValueError as error:
            assert str(error) == workflow_history.SENSITIVE_WORKFLOW_ERROR
        else:
            raise AssertionError("敏感输出不得保存")

        assert workflow_history.get_workflow_run("workflow-sensitive") is None

        sensitive_metadata = WorkflowResult(
            workflow_id="workflow-sensitive-metadata",
            workflow_type="client_project",
            status="completed",
            steps=[AgentResult(
                "task-sensitive-metadata",
                "Search Agent",
                "completed",
                "safe output",
            )],
            final_output="safe output",
            override_reason="API Key: secret",
        )
        try:
            workflow_history.save_workflow_run(
                "普通项目", "测试背景", sensitive_metadata
            )
        except ValueError as error:
            assert str(error) == workflow_history.SENSITIVE_WORKFLOW_ERROR
        else:
            raise AssertionError("敏感元数据不得保存")

        assert workflow_history.get_workflow_run(
            "workflow-sensitive-metadata"
        ) is None
    finally:
        workflow_history.DB_PATH = original_db_path

print("Workflow-history tests passed.")
