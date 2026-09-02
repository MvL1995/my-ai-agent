from dataclasses import dataclass

from task_contract import AgentResult


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_type: str
    status: str
    steps: list[AgentResult]
    final_output: str
    error: str | None = None
