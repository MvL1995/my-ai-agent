(() => {
  const form = document.getElementById("lead-form");
  const success = document.getElementById("lead-success");
  const status = form.querySelector('[role="status"]');
  const submit = form.querySelector('[type="submit"]');
  let submitting = false;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submitting || !form.reportValidity()) return;
    const payload = Object.fromEntries(new FormData(form));
    const query = new URLSearchParams(location.search);
    payload.source_workflow_id = "workflow-39cc14c9de2c4ce8bd6b145a96fadb5e";
    payload.utm_source = query.get("utm_source") || "direct";
    payload.utm_medium = query.get("utm_medium") || "";
    payload.utm_campaign = query.get("utm_campaign") || "";
    if (payload.website) return;
    submitting = true;
    submit.disabled = true;
    status.textContent = "正在提交，请稍候…";
    try {
      const response = await fetch("https://formspree.io/f/mdeoppza", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("submit failed");
      form.reset();
      form.hidden = true;
      success.hidden = false;
      success.focus();
    } catch {
      status.textContent = "提交失败，请稍后重试。";
      status.dataset.state = "error";
    } finally {
      submitting = false;
      submit.disabled = false;
    }
  });
})();
