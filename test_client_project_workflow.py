import importlib.util
import json
import time


contract_spec = importlib.util.find_spec("workflow_contract")
workflow_spec = importlib.util.find_spec(
    "client_project_workflow"
)

assert contract_spec is not None, (
    "workflow_contract.py 尚未实现"
)
assert workflow_spec is not None, (
    "client_project_workflow.py 尚未实现"
)

from client_project_workflow import (
    run_client_project_workflow,
)
from landing_page_package import LEAD_CAPTURE_SCRIPT
from workflow_contract import WorkflowResult


received_tasks = []
coding_files = {
    "index.html": (
        "<main>Hello</main><form id='lead-form'>"
        "<input name='name' required>"
        "<input name='email' type='email' required><input name='company'>"
        "<select name='intent' required><option value='project'></option>"
        "<option value='booking'></option></select>"
        "<input name='preferred_time' type='datetime-local'>"
        "<textarea name='message'></textarea>"
        "<div class='honeypot'><input name='website'></div>"
        "<button type='submit'>Send</button>"
        "<p role='status' aria-live='polite'></p></form>"
        "<a data-lead-intent='booking' href='#lead-form'>Book</a>"
        "<script src='script.js'></script>"
    ),
    "styles.css": ".honeypot { display: none; }",
    "script.js": "",
}
coding_output = json.dumps(coding_files)
validated_coding_files = {**coding_files, "script.js": LEAD_CAPTURE_SCRIPT}
validated_coding_output = json.dumps(validated_coding_files, ensure_ascii=False)


def handler(output):
    def run(task):
        received_tasks.append(task)
        return output

    return run


result = run_client_project_workflow(
    "为客户制定网站与广告启动计划",
    "客户经营吉隆坡本地餐厅",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": handler(coding_output),
        "QA Agent": handler("结论：通过"),
        "Client Project Manager Agent": handler(
            "项目计划完成"
        ),
    },
)

assert isinstance(result, WorkflowResult)
assert result.workflow_id.startswith("workflow-")
assert result.workflow_type == "client_project"
assert result.status == "completed"
assert result.final_output == "项目计划完成"
assert result.error is None
assert result.failed_stage is None
assert [step.agent_name for step in result.steps] == [
    "Search Agent",
    "Strategy Agent",
    "Copywriting Agent",
    "Web Design Agent",
    "Coding Agent",
    "QA Agent",
    "Client Project Manager Agent",
]
assert result.duration_ms > 0
assert result.duration_ms == sum(step.duration_ms for step in result.steps)

assert received_tasks[0].task_type == "research"
assert received_tasks[0].context == (
    "客户经营吉隆坡本地餐厅"
)

assert received_tasks[1].task_type == "strategy"
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[1].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[1].context
)

assert received_tasks[2].task_type == "copywriting"
assert "Research 输出：\nResearch 完成" in (
    received_tasks[2].context
)
assert "Strategy 输出：\nStrategy 完成" in (
    received_tasks[2].context
)

assert received_tasks[3].task_type == "web_design"
assert "Copywriting 输出：\nCopywriting 完成" in (
    received_tasks[3].context
)

assert received_tasks[4].task_type == "coding"
assert received_tasks[4].objective == (
    "生成可交付 Landing Page 网站包。\n"
    "原始项目目标：为客户制定网站与广告启动计划"
)
assert "Web Design 输出：\nWeb Design 完成" in (
    received_tasks[4].context
)

assert received_tasks[5].task_type == "qa"
assert f"Coding 输出：\n{validated_coding_output}" in (
    received_tasks[5].context
)
assert result.landing_page.files == validated_coding_files

assert received_tasks[6].task_type == (
    "client_management"
)
assert "原始项目背景：\n客户经营吉隆坡本地餐厅" in (
    received_tasks[6].context
)
assert "Research 输出：\nResearch 完成" in (
    received_tasks[6].context
)
assert "Strategy 输出：\nStrategy 完成" in (
    received_tasks[6].context
)
assert "QA 输出：\n结论：通过" in (
    received_tasks[6].context
)

retry_tasks = []


def retry_coding_handler(task):
    retry_tasks.append(task)
    if len(retry_tasks) == 1:
        time.sleep(0.02)
        return "not json"
    return coding_output


retry_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": retry_coding_handler,
        "QA Agent": handler("结论：通过"),
        "Client Project Manager Agent": handler("项目计划完成"),
    },
)

assert retry_result.status == "completed"
assert retry_result.landing_page.files == validated_coding_files
assert len(retry_tasks) == 2
assert retry_result.steps[4].duration_ms >= 15
assert "Coding Agent 必须返回有效 JSON。" in retry_tasks[1].context

contract_retry_tasks = []


def contract_retry_handler(task):
    contract_retry_tasks.append(task)
    if len(contract_retry_tasks) == 1:
        return json.dumps({
            **coding_files,
            "index.html": coding_files["index.html"].replace("data-lead-intent", "missing"),
        })
    return coding_output


contract_retry_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": contract_retry_handler,
        "QA Agent": handler("结论：通过"),
        "Client Project Manager Agent": handler("项目计划完成"),
    },
)
assert contract_retry_result.status == "completed"
assert len(contract_retry_tasks) == 2
assert "data-lead-intent=booking" in contract_retry_tasks[1].context
assert contract_retry_result.landing_page.files == validated_coding_files


def must_not_run(task):
    raise AssertionError(
        f"{task.assigned_agent} 不应在 Coding 验证失败后运行"
    )


invalid_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": handler("not json"),
        "QA Agent": must_not_run,
        "Client Project Manager Agent": must_not_run,
    },
)

assert invalid_result.status == "failed"
assert len(invalid_result.steps) == 5
assert invalid_result.steps[-1].agent_name == "Coding Agent"
assert invalid_result.steps[-1].status == "failed"
assert invalid_result.landing_page is None
assert "必须返回有效 JSON" in invalid_result.error

qa_rework_coding_tasks = []
qa_rework_qa_tasks = []
revised_coding_files = {
    **coding_files,
    "index.html": coding_files["index.html"].replace("Hello", "Revised"),
}
revised_coding_output = json.dumps(revised_coding_files)


def qa_rework_coding_handler(task):
    qa_rework_coding_tasks.append(task)
    if len(qa_rework_coding_tasks) == 1:
        return coding_output
    return revised_coding_output


def qa_rework_handler(task):
    qa_rework_qa_tasks.append(task)
    if len(qa_rework_qa_tasks) == 1:
        return "## 结论：需修改\n问题：CTA 不清晰。"
    return "结论：通过"


qa_rework_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": qa_rework_coding_handler,
        "QA Agent": qa_rework_handler,
        "Client Project Manager Agent": handler("项目计划完成"),
    },
)

assert qa_rework_result.status == "completed"
assert len(qa_rework_coding_tasks) == 2
assert len(qa_rework_qa_tasks) == 2
assert qa_rework_result.landing_page.files == {**revised_coding_files, "script.js": LEAD_CAPTURE_SCRIPT}
assert [step.agent_name for step in qa_rework_result.steps[-5:]] == [
    "Coding Agent",
    "QA Agent",
    "Coding Agent",
    "QA Agent",
    "Client Project Manager Agent",
]
assert "QA 输出：\n## 结论：需修改" in qa_rework_coding_tasks[1].context
validated_revised_output = json.dumps({**revised_coding_files, "script.js": LEAD_CAPTURE_SCRIPT}, ensure_ascii=False)
assert f"Coding 输出：\n{validated_revised_output}" in (
    qa_rework_qa_tasks[1].context
)
for qa_task in qa_rework_qa_tasks:
    assert "平台集成事实（已由自动化测试验证）" in qa_task.context
    assert "POST /api/leads" in qa_task.context
    assert "不存在第三种组合意向" in qa_task.context
    assert "event.source" in qa_task.context
    assert "preferred_time 无需静态 required" in qa_task.context
    assert "message 为可选字段" in qa_task.context
    assert "状态区域初始可为空" in qa_task.context
    assert "平台注入固定线索提交脚本" in qa_task.context



qa_rejected_coding_calls = 0
qa_rejected_qa_calls = 0


def qa_rejected_coding_handler(task):
    global qa_rejected_coding_calls
    qa_rejected_coding_calls += 1
    return coding_output


def qa_rejected_handler(task):
    global qa_rejected_qa_calls
    qa_rejected_qa_calls += 1
    return "结论：需修改\n问题：仍有阻断缺陷。"


qa_rejected_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": qa_rejected_coding_handler,
        "QA Agent": qa_rejected_handler,
        "Client Project Manager Agent": must_not_run,
    },
)

assert qa_rejected_result.status == "failed"
assert qa_rejected_result.failed_stage == "QA Agent"
assert qa_rejected_coding_calls == 2
assert qa_rejected_qa_calls == 2
assert qa_rejected_result.steps[-1].status == "failed"
assert "返修后仍需修改" in qa_rejected_result.error


invalid_qa_result = run_client_project_workflow(
    "为客户制作 Landing Page",
    "测试背景",
    {
        "Search Agent": handler("Research 完成"),
        "Strategy Agent": handler("Strategy 完成"),
        "Copywriting Agent": handler("Copywriting 完成"),
        "Web Design Agent": handler("Web Design 完成"),
        "Coding Agent": handler(coding_output),
        "QA Agent": handler("结论：通过，但存在阻断缺陷"),
        "Client Project Manager Agent": must_not_run,
    },
)

assert invalid_qa_result.status == "failed"
assert invalid_qa_result.failed_stage == "QA Agent"
assert invalid_qa_result.steps[-1].status == "failed"
assert "必须明确返回结论" in invalid_qa_result.error
print("Client-project-workflow tests passed.")
