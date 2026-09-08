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
from workflow_contract import WorkflowResult


received_tasks = []
coding_files = {
    "index.html": "<main>Hello</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
coding_output = json.dumps(coding_files)


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
assert f"Coding 输出：\n{coding_output}" in (
    received_tasks[5].context
)
assert result.landing_page.files == coding_files

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
assert retry_result.landing_page.files == coding_files
assert len(retry_tasks) == 2
assert retry_result.steps[4].duration_ms >= 15
assert "Coding Agent 必须返回有效 JSON。" in retry_tasks[1].context


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
    "index.html": "<main>Revised</main>",
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
assert qa_rework_result.landing_page.files == revised_coding_files
assert [step.agent_name for step in qa_rework_result.steps[-5:]] == [
    "Coding Agent",
    "QA Agent",
    "Coding Agent",
    "QA Agent",
    "Client Project Manager Agent",
]
assert "QA 输出：\n## 结论：需修改" in qa_rework_coding_tasks[1].context
assert f"Coding 输出：\n{revised_coding_output}" in (
    qa_rework_qa_tasks[1].context
)


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
