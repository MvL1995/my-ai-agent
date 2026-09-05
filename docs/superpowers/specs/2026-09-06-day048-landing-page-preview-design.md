# Day048 Landing Page Preview Design

## Goal

Render the validated `LandingPagePackage` from Day047 inside the existing AI
Agency Operator Web UI so completed client workflows produce a visible landing
page preview.

## Architecture

Keep preview generation entirely in `web/index.html`. The existing workflow
API already returns `landing_page.files`, so Day048 adds no endpoint, database
table, dependency, or generated file on disk.

The Delivery panel gains one preview area containing a placeholder and a
sandboxed iframe. Both newly completed workflows and detailed history records
continue through the existing `renderRun(run)` function.

## Data Flow

When `renderRun(run)` receives a valid landing-page package, browser code:

1. parses `index.html` with `DOMParser`;
2. injects a restrictive Content Security Policy;
3. appends `styles.css` to the parsed document head;
4. appends `script.js` to the parsed document body;
5. assigns the completed document to the iframe `srcdoc` property.

The iframe uses `sandbox="allow-scripts"` without same-origin, popup, form, or
top-navigation permissions. The injected policy blocks network connections and
external resources while allowing inline CSS, inline JavaScript, and `data:`
images required by the self-contained preview.

## Empty and Failure States

If the workflow failed, has no `landing_page`, or has an incomplete client-side
shape, the UI clears any previous `srcdoc`, hides the iframe, and displays
`暂无可预览网页。`. Preview errors must not replace the workflow's text output,
step list, or status.

Generated markup is never inserted into the operator document with
`innerHTML`; it exists only inside the sandboxed iframe. Runtime errors inside
the generated page remain isolated from the operator UI.

## Scope

Day048 previews one self-contained landing page in the existing Delivery panel.
It does not add editing, responsive device controls, downloads, deployment,
filesystem export, external assets, or a separate preview server.

## Verification

- Extend `test_web_app.py` to check the preview elements and sandbox policy.
- Check that the shared run renderer receives landing-page data for both live
  and historical workflow responses.
- Check that missing or failed packages reset the preview state.
- Run complete project verification and create a checkpoint.
- Manually verify one new workflow and one historical workflow in the browser.
