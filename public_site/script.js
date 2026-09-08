(() => {
  const form = document.getElementById("lead-form");
  const status = form.querySelector('[role="status"]');
  const submit = form.querySelector('[type="submit"]');
  const intent = form.elements.intent;
  const preferredTime = form.elements.preferred_time;
  let submitting = false;
  const show = (message, ok = false) => {
    status.textContent = message;
    status.dataset.state = ok ? "success" : "error";
  };
  const reset = () => {
    form.reset();
    preferredTime.required = false;
  };
  document.querySelectorAll('[data-lead-intent="booking"]').forEach((entry) => {
    entry.addEventListener("click", () => {
      intent.value = "booking";
      preferredTime.required = true;
    });
  });
  intent.addEventListener("change", () => {
    preferredTime.required = intent.value === "booking";
  });
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
      reset();
      show("已收到请求，我们会通过邮箱回复。", true);
    } catch {
      show("提交失败，请稍后重试。");
    } finally {
      submitting = false;
      submit.disabled = false;
    }
  });
})();
