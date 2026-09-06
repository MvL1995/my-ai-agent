# Day051 Structured Project Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and validate a seven-field `ProjectBrief`, then feed it through the existing Web workflow without changing downstream Agents.

**Architecture:** `workflow_contract.py` owns the brief contract and validation. `web_app.py` converts a valid brief to the existing workflow command, while `web/index.html` collects the seven fields and keeps native browser validation.

**Tech Stack:** Python standard library, dataclasses, existing HTTP server, vanilla HTML/CSS/JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-06-day051-structured-project-brief-design.md`

## Global Constraints

- All seven fields are required non-empty strings after trimming.
- The server remains the authoritative validation boundary.
- Keep both existing terminal workflow command formats compatible.
- Add no dependency, database migration, or downstream Agent change.
- Preserve the existing background job, history, preview, and ZIP flows.

---

### Task 1: Add the ProjectBrief contract

**Files:**
- Modify: `workflow_contract.py`
- Create: `test_project_brief.py`

**Interfaces:**
- Consumes: a JSON-like `dict` supplied by the Web boundary.
- Produces: `create_project_brief(payload: dict) -> ProjectBrief`.

- [ ] **Step 1: Write the failing contract test**

```python
from workflow_contract import ProjectBrief, create_project_brief


payload = {
    "company_name": " Alpha Studio ",
    "target_customer": " Malaysian SMEs ",
    "core_service": " AI websites ",
    "region": " Malaysia ",
    "language": " Chinese ",
    "cta": " Book a consultation ",
    "contact": " WhatsApp: +60123456789 ",
}

brief = create_project_brief(payload)
assert isinstance(brief, ProjectBrief)
assert brief.company_name == "Alpha Studio"
assert brief.contact == "WhatsApp: +60123456789"

try:
    create_project_brief({**payload, "company_name": " ", "cta": None})
except ValueError as error:
    assert str(error) == "Invalid project brief fields: company_name, cta"
else:
    raise AssertionError("Invalid fields must raise ValueError")

print("Project-brief tests passed.")
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python test_project_brief.py`

Expected: import failure because `ProjectBrief` does not exist.

- [ ] **Step 3: Add the minimal contract and validator**

```python
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
        if not isinstance(payload.get(field), str)
        or not payload[field].strip()
    ]
    if invalid_fields:
        raise ValueError(
            "Invalid project brief fields: "
            + ", ".join(invalid_fields)
        )

    return ProjectBrief(**{
        field: payload[field].strip()
        for field in PROJECT_BRIEF_FIELDS
    })
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `python test_project_brief.py`

Expected: `Project-brief tests passed.`

---

### Task 2: Connect the structured brief to the Web workflow

**Files:**
- Modify: `web_app.py`
- Modify: `web/index.html`
- Modify: `test_web_app.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `create_project_brief(payload: dict) -> ProjectBrief`.
- Produces: the existing `客户项目：目标 | 项目背景` command and unchanged job response.

- [ ] **Step 1: Update the Web test to require structured input**

Create one reusable payload in `test_web_app.py`:

```python
project_payload = {
    "company_name": "Alpha Studio",
    "target_customer": "Malaysian SMEs",
    "core_service": "AI websites and digital advertising",
    "region": "Malaysia",
    "language": "Chinese",
    "cta": "Book a consultation",
    "contact": "WhatsApp: +60123456789",
}
```

Use it for the successful request. Assert that the received command contains every value. Submit a second payload with `company_name` and `cta` invalid and assert:

```python
assert status == 400
assert error["error"] == (
    "Invalid project brief fields: company_name, cta"
)
```

Assert the page contains `name="company_name"` through `name="contact"` and posts the structured payload.

- [ ] **Step 2: Run the Web test and verify RED**

Run: `python test_web_app.py`

Expected: the old API rejects the new payload or the page lacks the new controls.

- [ ] **Step 3: Replace the Web boundary validation**

Import `create_project_brief` in `web_app.py`. Replace the `objective/context` loop with:

```python
try:
    brief = create_project_brief(payload)
except ValueError as error:
    self.send_json(400, {"error": str(error)})
    return

objective = (
    f"为「{brief.company_name}」制作客户转化型网站包"
)
context = "；".join((
    f"公司名称：{brief.company_name}",
    f"目标客户：{brief.target_customer}",
    f"核心服务：{brief.core_service}",
    f"地区：{brief.region}",
    f"语言：{brief.language}",
    f"行动号召：{brief.cta}",
    f"联系方式：{brief.contact}",
))
command = f"客户项目：{objective} | {context}"
```

Do not change the worker, history, preview, or download code.

- [ ] **Step 4: Replace the two-field form with seven native controls**

Use the exact field names from `PROJECT_BRIEF_FIELDS`. Keep `required`, visible labels, helpers, and the existing live status element. In JavaScript, collect and validate the seven controls, then submit:

```javascript
const fieldNames = [
  "company_name", "target_customer", "core_service",
  "region", "language", "cta", "contact"
];
const payload = Object.fromEntries(
  fieldNames.map((name) => [name, form.elements[name].value.trim()])
);
```

Use a native `<select>` for language with Chinese, English, and bilingual choices. Keep all other controls as native inputs or textareas.

- [ ] **Step 5: Run focused and full verification**

Run:

```powershell
python test_project_brief.py
python test_web_app.py
python checkpoint_project.py
```

Expected: all tests pass and a new checkpoint is created.

- [ ] **Step 6: Record Day051 completion**

Append to `PROGRESS.md`:

```markdown
## Day051 — Complete

- Added a validated seven-field `ProjectBrief` for Web client intake.
- Converted structured briefs into the existing client-project workflow.
- Preserved terminal commands, background execution, history, preview, and ZIP delivery.
- Added no dependency or database migration.
- Verification: `python checkpoint_project.py` — all tests passed.
```

- [ ] **Step 7: Commit**

```powershell
git add workflow_contract.py web_app.py web/index.html test_project_brief.py test_web_app.py PROGRESS.md docs/superpowers/specs/2026-09-06-day051-structured-project-brief-design.md docs/superpowers/plans/2026-09-06-day051-structured-project-brief.md
git commit -m "feat: add structured project brief"
```
