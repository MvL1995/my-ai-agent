# Day051 Structured Project Brief Design

## Goal

Replace the two-field Web intake with a validated seven-field client brief so downstream agents receive enough facts to build a usable landing page without guessing.

## Required fields

- `company_name`
- `target_customer`
- `core_service`
- `region`
- `language`
- `cta`
- `contact`

Every value must be a non-empty string after trimming. The server is the authoritative validation boundary; browser validation exists only for immediate feedback.

## Architecture

Add `ProjectBrief` and its small constructor to `workflow_contract.py`. The Web API creates the contract from JSON, converts it into the existing `objective` and `context` workflow inputs, then uses the unchanged background job and seven-agent pipeline.

No dependency, database, Agent, history schema, or package contract changes are required.

## Data flow

1. The browser submits the seven fields to `POST /api/workflows`.
2. The server trims and validates all fields together.
3. The server builds this objective: `为「{company_name}」制作客户转化型网站包`.
4. The server builds labeled context containing all seven fields.
5. The existing `execute_workflow_request()` runs in the existing background worker.
6. Existing history, preview, and ZIP delivery behavior remains unchanged.

## Error handling

- A non-object JSON body remains `400`.
- Missing, non-string, or whitespace-only values return `400` and name every invalid field.
- Existing sensitive-content checks remain authoritative.
- Background Agent failures continue to appear through the existing job status API.
- Contact accepts a phone number, WhatsApp value, email, or URL; Day051 does not add format-specific validation.

## Compatibility

The terminal `客户项目：目标 | 项目背景` and `工作流：client_project | ...` commands remain supported. The internal Web API now requires the structured brief.

## Testing

- Contract creation trims valid values.
- Contract creation reports all invalid fields.
- The Web API rejects incomplete briefs.
- A valid Web brief returns immediately, reaches the existing executor, and preserves every field in the generated command.
- The page contains all seven controls and submits the structured payload.
- Full project verification remains green.

## Out of scope

- Strict phone, email, or URL validation.
- Persisting editable draft briefs.
- New database tables or migrations.
- Changes to specialist Agent prompts.
- Authentication or multi-client accounts.
