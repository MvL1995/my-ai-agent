import importlib.util


module_spec = importlib.util.find_spec("workflow_entry")
assert module_spec is not None, "workflow_entry.py 尚未实现"

from workflow_contract import WorkflowResult
from workflow_entry import (
    WORKFLOW_COMMAND_USAGE,
    execute_workflow_request,
    extract_workflow_request,
)


assert extract_workflow_request("你好") is None
assert extract_workflow_request(
    "工作流： client_project | 启动客户项目 | 餐厅客户 "
) == (
    "client_project",
    "启动客户项目",
    "餐厅客户",
)
assert extract_workflow_request(
    "客户项目： 启动客户项目 | 餐厅客户 "
) == (
    "client_project",
    "启动客户项目",
    "餐厅客户",
)

received = {}
saved = {}


def fake_workflow(objective, context, handlers):
    received["objective"] = objective
    received["context"] = context
    received["handlers"] = handlers
    return WorkflowResult(
        workflow_id="workflow-test",
        workflow_type="client_project",
        status="completed",
        steps=[],
        final_output="客户项目计划",
    )


def fake_save(objective, context, result):
    saved["objective"] = objective
    saved["context"] = context
    saved["result"] = result


handlers = {"Search Agent": object()}
result = execute_workflow_request(
    "客户项目：启动客户项目 | 餐厅客户",
    handlers,
    run_workflow=fake_workflow,
    save_run=fake_save,
)

assert result.final_output == "客户项目计划"
assert received == {
    "objective": "启动客户项目",
    "context": "餐厅客户",
    "handlers": handlers,
}
assert saved == {
    "objective": "启动客户项目",
    "context": "餐厅客户",
    "result": result,
}

for invalid_input in (
    "工作流：",
    "工作流：client_project | 启动客户项目",
    "工作流：client_project | | 餐厅客户",
    "客户项目：",
    "客户项目：启动客户项目",
    "客户项目： | 餐厅客户",
):
    try:
        extract_workflow_request(invalid_input)
    except ValueError as error:
        assert str(error) == WORKFLOW_COMMAND_USAGE
    else:
        raise AssertionError(
            "无效工作流命令必须触发 ValueError"
        )

try:
    extract_workflow_request(
        "工作流：unknown | 启动客户项目 | 餐厅客户"
    )
except ValueError as error:
    assert str(error) == (
        "Unsupported workflow type: unknown"
    )
else:
    raise AssertionError(
        "未知工作流类型必须触发 ValueError"
    )

calls = {"run": 0, "save": 0}


def counting_workflow(objective, context, handlers):
    calls["run"] += 1
    return fake_workflow(objective, context, handlers)


def counting_save(objective, context, result):
    calls["save"] += 1


counted_result = execute_workflow_request(
    "客户项目：启动客户项目 | 普通背景",
    handlers,
    run_workflow=counting_workflow,
    save_run=counting_save,
)
assert counted_result.final_output == "客户项目计划"
assert calls == {"run": 1, "save": 1}

for sensitive_input in (
    "客户项目：保存 API Key | 普通背景",
    "客户项目：普通目标 | password=secret",
):
    try:
        execute_workflow_request(
            sensitive_input,
            handlers,
            run_workflow=counting_workflow,
            save_run=counting_save,
        )
    except ValueError as error:
        assert "拒绝工作流" in str(error)
    else:
        raise AssertionError("敏感工作流输入必须被拒绝")

assert calls == {"run": 1, "save": 1}

print("Workflow-entry tests passed.")
