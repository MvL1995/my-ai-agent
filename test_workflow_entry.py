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

received = {}


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


handlers = {"Search Agent": object()}
result = execute_workflow_request(
    "工作流：client_project | 启动客户项目 | 餐厅客户",
    handlers,
    run_workflow=fake_workflow,
)

assert result.final_output == "客户项目计划"
assert received == {
    "objective": "启动客户项目",
    "context": "餐厅客户",
    "handlers": handlers,
}

for invalid_input in (
    "工作流：",
    "工作流：client_project | 启动客户项目",
    "工作流：client_project | | 餐厅客户",
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

print("Workflow-entry tests passed.")
