import json
from uuid import uuid4

from landing_page_package import (
    parse_landing_page_package,
    validate_lead_capture_package,
)
from task_executor import execute_task
from task_router import route_task
from workflow_contract import WorkflowResult


QA_VERDICT_ERROR = "必须明确返回结论：通过或结论：需修改。"
QA_PLATFORM_CONTEXT = (
    "\n\n平台集成事实（已由自动化测试验证）：\n"
    "POST /api/leads 校验输入并持久化线索；\n"
    "intent 只允许 project 或 booking，不存在第三种组合意向；\n"
    "硬契约齐全时，增强建议不得阻断结论通过。\n"
    "预览父页校验 event.source、调用该接口并回传 lead-result。\n"
    "平台注入固定线索提交脚本，负责 iframe lead-submit/lead-result、"
    "独立 POST /api/leads 与 response.ok 状态处理；\n"
    "生成三文件包的 script.js 必须为空，QA 不得以缺少客户端脚本阻断；\n"
    "preferred_time 无需静态 required，message 为可选字段；\n"
    "状态区域初始可为空，固定脚本会写入提交中、成功或失败状态。"
)
PIPELINE = (
    ("research", "Research", ()),
    ("strategy", "Strategy", ("Research",)),
    (
        "copywriting",
        "Copywriting",
        ("Research", "Strategy"),
    ),
    (
        "web_design",
        "Web Design",
        ("Strategy", "Copywriting"),
    ),
    (
        "coding",
        "Coding",
        ("Copywriting", "Web Design"),
    ),
    (
        "qa",
        "QA",
        ("Copywriting", "Web Design", "Coding"),
    ),
    (
        "client_management",
        "Client Project Manager",
        (
            "Research",
            "Strategy",
            "Copywriting",
            "Web Design",
            "Coding",
            "QA",
        ),
    ),
)


def _run_step(
    task_type,
    objective,
    context,
    handlers,
):
    task = route_task(
        task_type,
        objective,
        context,
    )
    return execute_task(task, handlers)


def _failed_workflow(workflow_id, steps):
    failed_step = steps[-1]
    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="failed",
        steps=steps,
        final_output="",
        error=(
            f"{failed_step.agent_name}: "
            f"{failed_step.error}"
        ),
        duration_ms=sum(step.duration_ms for step in steps),
        failed_stage=failed_step.agent_name,
    )


def _build_step_context(context, outputs, dependencies):
    if not dependencies:
        return context

    blocks = [f"原始项目背景：\n{context}"]
    blocks.extend(
        f"{name} 输出：\n{outputs[name]}"
        for name in dependencies
    )
    return "\n\n".join(blocks)


def _qa_verdict(output):
    if not isinstance(output, str):
        return None

    first_line = next(
        (line.strip() for line in output.splitlines() if line.strip()),
        "",
    )
    first_line = first_line.lstrip("#").strip()
    if first_line == "结论：通过":
        return "passed"
    if first_line == "结论：需修改":
        return "needs_changes"
    return None


def run_client_project_workflow(
    objective,
    context,
    handlers,
):
    workflow_id = f"workflow-{uuid4().hex}"
    steps = []
    coding_objective = (
        "生成可交付 Landing Page 网站包。\n"
        f"原始项目目标：{objective}"
    )

    outputs = {}
    landing_page = None

    for task_type, output_name, dependencies in PIPELINE:
        step_objective = objective
        if task_type == "coding":
            step_objective = coding_objective

        step_context = _build_step_context(
            context,
            outputs,
            dependencies,
        )
        if task_type == "qa":
            step_context += QA_PLATFORM_CONTEXT

        step = _run_step(
            task_type,
            step_objective,
            step_context,
            handlers,
        )

        if step.status == "failed":
            steps.append(step)
            return _failed_workflow(workflow_id, steps)

        if output_name == "Coding":
            try:
                landing_page = parse_landing_page_package(step.output)
                landing_page = validate_lead_capture_package(landing_page)
            except ValueError as error:
                retry_context = _build_step_context(
                    context,
                    outputs,
                    dependencies,
                ) + (
                    f"\n\n上次输出校验失败：{error}\n"
                    "请修正并只返回完整的 Landing Page JSON。"
                )
                first_attempt_duration_ms = step.duration_ms
                step = _run_step(
                    task_type,
                    step_objective,
                    retry_context,
                    handlers,
                )
                step.duration_ms += first_attempt_duration_ms
                if step.status == "failed":
                    steps.append(step)
                    return _failed_workflow(workflow_id, steps)
                try:
                    landing_page = parse_landing_page_package(step.output)
                    landing_page = validate_lead_capture_package(landing_page)
                except ValueError as retry_error:
                    step.status = "failed"
                    step.error = str(retry_error)
                    steps.append(step)
                    return _failed_workflow(workflow_id, steps)

        if output_name == "QA" and _qa_verdict(step.output) is None:
            step.status = "failed"
            step.error = QA_VERDICT_ERROR
            steps.append(step)
            return _failed_workflow(workflow_id, steps)

        if output_name == "QA" and _qa_verdict(step.output) == "needs_changes":
            steps.append(step)
            rework_context = _build_step_context(
                context,
                outputs,
                dependencies[:-1],
            ) + (
                f"\n\nQA 输出：\n{step.output}\n"
                "请修正 QA 指出的问题，并只返回完整的 "
                "Landing Page JSON。"
            )
            rework_step = _run_step(
                "coding",
                coding_objective,
                rework_context,
                handlers,
            )
            if rework_step.status == "failed":
                steps.append(rework_step)
                return _failed_workflow(workflow_id, steps)
            try:
                landing_page = parse_landing_page_package(
                    rework_step.output
                )
                landing_page = validate_lead_capture_package(landing_page)
            except ValueError as error:
                rework_step.status = "failed"
                rework_step.error = str(error)
                steps.append(rework_step)
                return _failed_workflow(workflow_id, steps)

            steps.append(rework_step)
            outputs["Coding"] = json.dumps(landing_page.files, ensure_ascii=False)
            recheck_step = _run_step(
                "qa",
                objective,
                _build_step_context(
                    context,
                    outputs,
                    dependencies,
                ) + QA_PLATFORM_CONTEXT,
                handlers,
            )
            if recheck_step.status == "failed":
                steps.append(recheck_step)
                return _failed_workflow(workflow_id, steps)
            recheck_verdict = _qa_verdict(recheck_step.output)
            if recheck_verdict != "passed":
                recheck_step.status = "failed"
                recheck_step.error = (
                    "返修后仍需修改。"
                    if recheck_verdict == "needs_changes"
                    else QA_VERDICT_ERROR
                )
                steps.append(recheck_step)
                return _failed_workflow(workflow_id, steps)

            steps.append(recheck_step)
            outputs["QA"] = recheck_step.output
            continue

        steps.append(step)
        outputs[output_name] = (
            json.dumps(landing_page.files, ensure_ascii=False)
            if output_name == "Coding"
            else step.output
        )

    return WorkflowResult(
        workflow_id=workflow_id,
        workflow_type="client_project",
        status="completed",
        steps=steps,
        final_output=steps[-1].output,
        landing_page=landing_page,
        duration_ms=sum(step.duration_ms for step in steps),
    )
