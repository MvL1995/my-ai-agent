# Day048 Landing Page Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render each completed workflow's validated `LandingPagePackage` inside the existing Delivery panel.

**Architecture:** Keep the feature in the existing browser UI. `renderRun(run)` passes `run.landing_page` to one preview renderer, which combines the three package files with `DOMParser` and writes the result only to a sandboxed iframe through `srcdoc`.

**Tech Stack:** Existing HTML, CSS, browser JavaScript, Python standard-library HTTP tests

**Spec:** `docs/superpowers/specs/2026-09-06-day048-landing-page-preview-design.md`

## Global Constraints

- Add no endpoint, database table, dependency, generated file, or preview server.
- Reuse `renderRun(run)` for newly completed and historical workflows.
- Use `sandbox="allow-scripts"`; do not grant same-origin, popup, form, or top-navigation permissions.
- Inject a CSP that blocks network and external resources while allowing inline CSS, inline JavaScript, and `data:` images.
- Never insert generated markup into the operator document with `innerHTML`.
- Missing, incomplete, and failed packages must clear the old preview without replacing workflow output or steps.
- Do not add editing, device controls, downloads, deployment, filesystem export, or external assets.

---

### Task 1: Add the secure landing-page preview

**Files:**
- Modify: `test_web_app.py:127-133`
- Modify: `web/index.html:123-126, 195-198, 211-243, 245-248, 298-312`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: `run.landing_page.files` containing string values for `index.html`, `styles.css`, and `script.js`
- Produces: `renderLandingPagePreview(landingPage)` with no return value; it either displays a sandboxed preview or the empty state

- [ ] **Step 1: Add failing UI-contract assertions**

Add these assertions after the existing `history-list` assertion in `test_web_app.py`:

```python
        assert 'id="preview-empty"' in page
        assert 'id="preview-frame"' in page
        assert 'sandbox="allow-scripts"' in page
        assert "allow-same-origin" not in page
        assert "function renderLandingPagePreview(landingPage)" in page
        assert "new DOMParser()" in page
        assert 'default-src \'none\'' in page
        assert 'connect-src \'none\'' in page
        assert 'img-src data:' in page
        assert "previewFrame.srcdoc =" in page
        assert (
            'renderLandingPagePreview('
            'run.status === "completed" ? run.landing_page : null'
            ');'
        ) in page
        assert page.count("renderLandingPagePreview(null);") == 2
```

- [ ] **Step 2: Run the focused test and confirm the new contract fails**

Run:

```powershell
python test_web_app.py
```

Expected: failure on `assert 'id="preview-empty"' in page` because the preview UI does not exist yet.

- [ ] **Step 3: Add the preview layout and native iframe isolation**

Add these styles after the existing `.step p` rule in `web/index.html`:

```css
    .preview { margin-top: var(--space-5); border-top: 0.0625rem solid var(--color-rule); padding-top: var(--space-4); }
    .preview h3 { margin-bottom: var(--space-3); }
    .preview-frame {
      display: block;
      width: 100%;
      min-height: 30rem;
      border: 0.0625rem solid var(--color-rule);
      border-radius: var(--radius-sm);
      background: white;
    }
    .preview-frame[hidden] { display: none; }
```

Add this section after `result-steps` in the Delivery panel:

```html
          <section class="preview" aria-labelledby="preview-title">
            <h3 id="preview-title">Landing Page 预览</h3>
            <p class="empty" id="preview-empty">暂无可预览网页。</p>
            <iframe
              class="preview-frame"
              id="preview-frame"
              title="生成的 Landing Page 预览"
              sandbox="allow-scripts"
              hidden
            ></iframe>
          </section>
```

- [ ] **Step 4: Add one preview renderer and connect every run path**

Add these element references with the existing DOM references:

```javascript
    const previewEmpty = document.querySelector("#preview-empty");
    const previewFrame = document.querySelector("#preview-frame");
```

Add this function immediately before `renderRun(run)`:

```javascript
    function renderLandingPagePreview(landingPage) {
      previewFrame.removeAttribute("srcdoc");
      previewFrame.hidden = true;
      previewEmpty.hidden = false;

      const files = landingPage && landingPage.files;
      const requiredFiles = ["index.html", "styles.css", "script.js"];
      if (!files || !requiredFiles.every((name) => typeof files[name] === "string")) return;

      try {
        const document = new DOMParser().parseFromString(files["index.html"], "text/html");
        const policy = document.createElement("meta");
        policy.httpEquiv = "Content-Security-Policy";
        policy.content = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; form-action 'none'; base-uri 'none'";

        const style = document.createElement("style");
        style.textContent = files["styles.css"];
        const script = document.createElement("script");
        script.textContent = files["script.js"];

        document.head.prepend(policy);
        document.head.append(style);
        document.body.append(script);
        previewFrame.srcdoc = `<!doctype html>\n${document.documentElement.outerHTML}`;
        previewFrame.hidden = false;
        previewEmpty.hidden = true;
      } catch (error) {
        console.error("Landing page preview failed.", error);
      }
    }
```

Add this line at the end of `renderRun(run)`:

```javascript
      renderLandingPagePreview(run.status === "completed" ? run.landing_page : null);
```

Replace the `loadRun()` error path with this block so an invalid history request cannot leave a stale preview:

```javascript
      catch (error) {
        renderLandingPagePreview(null);
        output.textContent = error.message;
        statusDot.dataset.status = "failed";
      }
```

Add the same reset as the first line of the form submission error path:

```javascript
        renderLandingPagePreview(null);
```

- [ ] **Step 5: Run the focused test and syntax checks**

Run:

```powershell
python test_web_app.py
python -m py_compile web_app.py test_web_app.py
```

Expected:

```text
Web-app tests passed.
```

The compile command must exit with code `0` and no output.

- [ ] **Step 6: Verify live and historical previews in the browser**

Start the existing server:

```powershell
python web_app.py
```

Open `http://127.0.0.1:8000`, submit this brief, and wait for completion:

```text
目标：为吉隆坡咖啡馆制作一个单页 Landing Page
背景：主打手冲咖啡，受众是附近上班族，使用中文，包含预约行动按钮
```

Verify:

- the final text and Agent steps remain visible;
- the generated page appears under `Landing Page 预览`;
- selecting the new record from `最近任务` renders the same preview;
- selecting a failed or package-free record shows `暂无可预览网页。` and does not retain the prior page;
- DevTools shows the iframe has only `allow-scripts`, and network requests from the preview are blocked.

- [ ] **Step 7: Run full verification and create the checkpoint**

Run:

```powershell
python checkpoint_project.py
```

Expected: every source compile and every discovered test reports `[PASS]`, the summary has zero failures, and a new checkpoint path is printed.

- [ ] **Step 8: Record Day048 completion**

Append this exact section to `PROGRESS.md`:

```markdown

## Day048 — Complete

- Added a sandboxed Landing Page preview to the existing Delivery panel.
- Combined validated HTML, CSS, and JavaScript in-browser with no new backend or dependency.
- Added a restrictive preview CSP and stale-preview reset behavior.
- Extended `test_web_app.py` with the preview security contract.
- Verification: `python checkpoint_project.py` — 42/42 tests passed.
```

- [ ] **Step 9: Commit the completed feature**

```powershell
git add web/index.html test_web_app.py PROGRESS.md
git commit -m "feat: preview generated landing pages"
```

Expected: one commit containing only the Day048 UI, its regression assertions, and the progress entry.
