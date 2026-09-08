import json
import re
from html.parser import HTMLParser
from dataclasses import dataclass


REQUIRED_FILES = (
    "index.html",
    "styles.css",
    "script.js",
)
LEAD_CAPTURE_SCRIPT = """(() => {
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
  window.addEventListener("message", (event) => {
    if (event.source !== window.parent || event.data?.type !== "lead-result") return;
    submitting = false;
    submit.disabled = false;
    if (event.data.ok) {
      reset();
      show("已收到请求，我们会通过邮箱回复。", true);
    } else {
      show(event.data.error || "提交失败，请稍后重试。");
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submitting || !form.reportValidity()) return;
    const payload = Object.fromEntries(new FormData(form));
    if (payload.website) return;
    submitting = true;
    submit.disabled = true;
    status.textContent = "正在提交，请稍候…";
    if (window.parent !== window) {
      window.parent.postMessage({ type: "lead-submit", payload }, "*");
      return;
    }
    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
"""


@dataclass
class LandingPagePackage:
    files: dict[str, str]


def parse_landing_page_package(raw_output):
    if not isinstance(raw_output, str):
        raise ValueError("Coding Agent 输出必须是字符串。")

    try:
        files = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("Coding Agent 必须返回有效 JSON。") from error

    if not isinstance(files, dict):
        raise ValueError("Coding Agent JSON 必须是对象。")

    if set(files) != set(REQUIRED_FILES):
        raise ValueError(
            "Coding Agent JSON 必须且只能包含 "
            "index.html、styles.css、script.js。"
        )

    if any(not isinstance(files[name], str) for name in REQUIRED_FILES):
        raise ValueError("Landing Page 文件内容必须是字符串。")

    if not files["index.html"].strip():
        raise ValueError("index.html 不能为空。")

    if not files["styles.css"].strip():
        raise ValueError("styles.css 不能为空。")

    return LandingPagePackage(
        files={name: files[name] for name in REQUIRED_FILES}
    )


class _LeadCaptureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lead_forms = 0
        self.in_lead_form = False
        self.controls = {}
        self.intent_values = set()
        self.in_intent = False
        self.booking_entry = False
        self.containers = []
        self.website_classes = set()
        self.website_hidden = False
        self.submit_control = False
        self.status_region = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.scripts.append(attrs)
        if attrs.get("data-lead-intent") == "booking":
            self.booking_entry = True
        if tag == "form":
            if attrs.get("id") == "lead-form":
                self.lead_forms += 1
                self.in_lead_form = True
            return
        if not self.in_lead_form:
            return
        if tag in {"button", "input"} and attrs.get("type", "").lower() == "submit":
            self.submit_control = True
        if attrs.get("role") == "status" and attrs.get("aria-live"):
            self.status_region = True
        name = attrs.get("name")
        if tag in {"input", "select", "textarea"} and name:
            self.controls.setdefault(name, []).append((tag, attrs))
        if name == "website":
            self.website_classes.update(attrs.get("class", "").split())
            for _, classes, hidden in self.containers:
                self.website_classes.update(classes)
                self.website_hidden = self.website_hidden or hidden
            self.website_hidden = self.website_hidden or "hidden" in attrs
        if tag in {"div", "label", "fieldset"}:
            classes = set(attrs.get("class", "").split())
            self.containers.append((tag, classes, "hidden" in attrs))

        if tag == "select" and name == "intent":
            self.in_intent = True
        elif tag == "option" and self.in_intent:
            value = attrs.get("value")
            if value:
                self.intent_values.add(value)

    def handle_endtag(self, tag):
        if tag == "select":
            self.in_intent = False
        for index in range(len(self.containers) - 1, -1, -1):
            if self.containers[index][0] == tag:
                self.containers = self.containers[:index]
                break
        if tag == "form" and self.in_lead_form:
            self.in_lead_form = False
            self.in_intent = False
            self.containers.clear()


def validate_lead_capture_package(package):
    html = package.files["index.html"]
    styles = package.files["styles.css"]
    parser = _LeadCaptureParser()
    parser.feed(html)

    missing = []
    if parser.lead_forms != 1:
        missing.append("id=lead-form")

    expected_tags = {
        "name": "input",
        "email": "input",
        "company": "input",
        "intent": "select",
        "preferred_time": "input",
        "message": "textarea",
        "website": "input",
    }
    for name, tag in expected_tags.items():
        controls = parser.controls.get(name, [])
        if len(controls) != 1 or controls[0][0] != tag:
            missing.append(f"name={name}")
    if set(parser.controls) - set(expected_tags):
        missing.append("unexpected form fields")

    attributes = {
        name: parser.controls[name][0][1]
        for name in expected_tags
        if len(parser.controls.get(name, [])) == 1
    }
    for name in ("name", "email", "intent"):
        if "required" not in attributes.get(name, {}):
            missing.append(f"{name} required")
    if attributes.get("email", {}).get("type") != "email":
        missing.append("email type=email")
    if attributes.get("preferred_time", {}).get("type") != "datetime-local":
        missing.append("preferred_time type=datetime-local")
    if parser.intent_values != {"project", "booking"}:
        missing.append("intent values=project,booking")
    if not parser.booking_entry:
        missing.append("data-lead-intent=booking")
    if not parser.submit_control:
        missing.append("type=submit")
    if not parser.status_region:
        missing.append("role=status aria-live")
    website_type = attributes.get("website", {}).get("type")
    if parser.scripts != [{"src": "script.js"}]:
        missing.append("one script src=script.js")
    hidden_by_class = any(
        re.search(
            rf"\.{re.escape(name)}\b[^{{,]*\{{[^}}]*(?:display\s*:\s*none|position\s*:\s*absolute[^}}]*(?:left|right)\s*:\s*-\d)",
            styles,
            re.IGNORECASE,
        )
        for name in parser.website_classes
    )
    if website_type != "hidden" and not parser.website_hidden and not hidden_by_class:
        missing.append("hidden website honeypot")

    if missing:
        raise ValueError(
            "Landing Page 缺少线索采集协议："
            + "、".join(dict.fromkeys(missing))
        )

    return LandingPagePackage(
        files={**package.files, "script.js": LEAD_CAPTURE_SCRIPT}
    )
