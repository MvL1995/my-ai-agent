import importlib.util


module_spec = importlib.util.find_spec("task_pipeline")
assert module_spec is not None, "task_pipeline.py 尚未实现"

from task_contract import AgentResult, TaskBrief
from task_pipeline import run_task_pipeline


received_tasks = []


def successful_handler(task):
    received_tasks.append(task)
    return "研究任务已完成"


completed = run_task_pipeline(
    "  ReSeArCh  ",
    "研究客户市场",
    "客户经营本地餐厅",
    {"Search Agent": successful_handler},
)

assert isinstance(completed, AgentResult)
assert completed.status == "completed"
assert completed.agent_name == "Search Agent"
assert completed.output == "研究任务已完成"
assert completed.error is None
assert len(received_tasks) == 1
assert isinstance(received_tasks[0], TaskBrief)
assert received_tasks[0].task_type == "research"
assert received_tasks[0].objective == "研究客户市场"
assert received_tasks[0].context == "客户经营本地餐厅"
assert completed.task_id == received_tasks[0].task_id


def failing_handler(task):
    raise RuntimeError("专业 Agent 执行失败")


failed = run_task_pipeline(
    "research",
    "研究竞争对手",
    "客户准备进入新市场",
    {"Search Agent": failing_handler},
)

assert failed.status == "failed"
assert failed.agent_name == "Search Agent"
assert failed.output == ""
assert failed.error == "专业 Agent 执行失败"

for arguments in (
    (
        "unknown",
        "执行未知任务",
        "测试背景",
        {"Search Agent": successful_handler},
    ),
    (
        "research",
        "研究客户市场",
        "测试背景",
        {},
    ),
):
    try:
        run_task_pipeline(*arguments)
    except ValueError:
        pass
    else:
        raise AssertionError("无效流水线配置必须触发 ValueError")

print("Task-pipeline tests passed.")
