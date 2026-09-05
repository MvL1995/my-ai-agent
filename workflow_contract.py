from dataclasses import dataclass

from landing_page_package import LandingPagePackage
from task_contract import AgentResult


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_type: str
    status: str
    steps: list[AgentResult]
    final_output: str
    error: str | None = None
    landing_page: LandingPagePackage | None = None
