# Sean Lam Insurance Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the selected option-3 Sean Lam insurance landing page with qualified WhatsApp entry, an exposure calculator, accessible FAQ interactions, and conservative insurance wording.

**Architecture:** Add a self-contained static client site under `client_sites/sean_lam/`; leave the live ProofFirst `public_site` untouched. Keep interaction logic as two pure JavaScript functions plus minimal DOM wiring so behavior is testable without browser dependencies.

**Tech Stack:** HTML5, CSS, browser JavaScript, Python assertion test, Node.js runtime check.

**Spec:** `docs/superpowers/specs/2026-09-09-sean-lam-insurance-site-design.md`

## Global Constraints

- Use the selected option-3 mockup as the visual source of truth.
- Preserve Sean's supplied portrait without face alteration.
- Do not invent a WhatsApp phone number or insurance claims.
- Add no runtime dependency and do not modify `public_site`.
- Follow red-green-refactor for observable behavior.

---

### Task 1: Contract and interactive behavior

**Files:**
- Create: `test_sean_lam_site.py`
- Create: `client_sites/sean_lam/index.html`
- Create: `client_sites/sean_lam/styles.css`
- Create: `client_sites/sean_lam/script.js`
- Create: `client_sites/sean_lam/assets/sean-lam.jpeg`

**Interfaces:**
- Consumes: the supplied portrait and the copy/interaction requirements in the spec.
- Produces: `calculateExposure(essentials, commitments, months): number` and `buildWhatsAppUrl(intent): string` from `script.js`, plus the complete semantic page.

- [ ] **Step 1: Write the failing contract test**

Create `test_sean_lam_site.py` to parse the real HTML, assert the required sections and cautious copy, verify all CTA and enquiry-intent controls, require accessible FAQ buttons, and run Node assertions against these hand-derived values:

```javascript
assert.equal(calculateExposure(2500, 1500, 6), 24000);
assert.equal(calculateExposure(-1, 100, 6), 600);
assert.match(buildWhatsAppUrl("existing"), /^https:\/\/wa\.me\/\?text=/);
assert.match(decodeURIComponent(buildWhatsAppUrl("existing")), /已经有保险/);
```

- [ ] **Step 2: Verify the test fails for the missing site**

Run: `python test_sean_lam_site.py`

Expected: FAIL because `client_sites/sean_lam/index.html` does not exist.

- [ ] **Step 3: Implement the minimum complete site**

Create the four static files and copy the supplied portrait. Implement the selected editorial design, all sections in the spec, the pure calculation and URL builders, and only the DOM listeners required for the calculator, intent selection, FAQ rows, and CTAs.

- [ ] **Step 4: Verify focused behavior passes**

Run: `python test_sean_lam_site.py`

Expected: `Sean Lam site tests passed.`

### Task 2: Visual and regression gate

**Files:**
- Create: `client_sites/sean_lam/design-qa.md`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: selected mockup, rendered local site, and Task 1 behavior.
- Produces: a passed Product Design QA record and project progress entry.

- [ ] **Step 1: Run all project checks**

Run: `python verify_project.py`

Expected: all discovered tests pass, including `test_sean_lam_site.py`.

- [ ] **Step 2: Capture and compare desktop and mobile**

Render the site at 1440px and 390px widths, exercise enquiry selection, calculator, FAQ, navigation, and WhatsApp URL creation, and check the browser console.

- [ ] **Step 3: Fix blocking visual differences**

Correct every P0/P1/P2 issue found against the selected mockup and repeat the same-state comparison until the report says `final result: passed`.

- [ ] **Step 4: Update progress and commit**

Document the separate client-site deliverable, verification count, and remaining deployment input; commit only the Sean site, its tests, QA evidence, plan/spec, and progress entry.
