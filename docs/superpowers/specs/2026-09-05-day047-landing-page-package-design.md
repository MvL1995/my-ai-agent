# Day047 Landing Page Package Design

## Goal

Turn the Coding Agent output in the existing landing-page workflow into a
validated, structured package that the Web UI and future delivery steps can
consume safely.

## Contract

Add `LandingPagePackage` with one `files` mapping. The mapping must contain
exactly these keys:

- `index.html`
- `styles.css`
- `script.js`

The Coding Agent must return one JSON object with those three keys and string
values. It must not wrap the JSON in Markdown fences or add explanatory text.
HTML and CSS must contain non-whitespace content. JavaScript may be an empty
string because a static landing page may not need it.

## Validation

Add a standard-library JSON parser that rejects:

- invalid JSON or a non-object root;
- missing or additional keys;
- non-string file contents;
- empty HTML or CSS.

Validation runs immediately after the Coding Agent completes. Invalid output
changes that Coding step to `failed`, records a clear validation error, and
stops the workflow before QA or Client Project Manager runs.

## Data Flow

On valid output, the existing raw Coding response continues downstream so the
current dependency flow stays unchanged. The parsed package is also attached to
`WorkflowResult.landing_page`. The existing Web API serialization then exposes
the package without a new endpoint.

Workflow history does not need a database migration. The stored Coding step
already contains the complete JSON. Detailed-history reads reconstruct the
optional package from that step; older or invalid records return `null`.

## Scope

Day047 does not write generated files to disk, execute generated code, add a
preview server, or add dependencies. The Client Project Manager text remains
the workflow `final_output`; `landing_page` is the machine-readable deliverable.

## Verification

- Test valid parsing and every rejected input class.
- Test that valid Coding output reaches QA and appears in the workflow result.
- Test that invalid Coding output stops QA and later steps.
- Test package reconstruction from workflow history.
- Run complete project verification and create a checkpoint.
