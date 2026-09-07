from dataclasses import dataclass

from landing_page_package import LandingPagePackage
from task_contract import AgentResult


PROJECT_BRIEF_FIELDS = (
    "company_name",
    "target_customer",
    "core_service",
    "region",
    "language",
    "cta",
    "contact",
)


@dataclass(frozen=True)
class ProjectBrief:
    company_name: str
    target_customer: str
    core_service: str
    region: str
    language: str
    cta: str
    contact: str


def create_project_brief(payload):
    invalid_fields = [
        field
        for field in PROJECT_BRIEF_FIELDS
        if not isinstance(payload.get(field), str) or not payload[field].strip()
    ]
    if invalid_fields:
        raise ValueError("Invalid project brief fields: " + ", ".join(invalid_fields))

    return ProjectBrief(
        **{field: payload[field].strip() for field in PROJECT_BRIEF_FIELDS}
    )


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_type: str
    status: str
    steps: list[AgentResult]
    final_output: str
    error: str | None = None
    landing_page: LandingPagePackage | None = None
    duration_ms: float = 0.0
    failed_stage: str | None = None
    retry_of: str | None = None
    attempt_number: int = 1
    override_source: str | None = None
    override_reason: str | None = None
