from dataclasses import dataclass


@dataclass
class TaskBrief:
    task_id: str
    task_type: str
    objective: str
    context: str
    assigned_agent: str


@dataclass
class AgentResult:
    task_id: str
    agent_name: str
    status: str
    output: str
    error: str | None = None
    duration_ms: float = 0.0
