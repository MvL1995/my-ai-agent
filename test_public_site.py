import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


SITE = Path(__file__).parent / "public_site"
required = {
    "index.html", "styles.css", "script.js", "privacy.html",
    "robots.txt", "vercel.json",
}
assert {path.name for path in SITE.iterdir() if path.is_file()} == required

index = (SITE / "index.html").read_text(encoding="utf-8")
script = (SITE / "script.js").read_text(encoding="utf-8")
privacy = (SITE / "privacy.html").read_text(encoding="utf-8")
config = json.loads((SITE / "vercel.json").read_text(encoding="utf-8"))
styles = (SITE / "styles.css").read_text(encoding="utf-8")

endpoint = re.search(r'action="(https://formspree.io/f/[A-Za-z0-9]+)"', index)
assert endpoint
assert endpoint.group(1) in script
tags = Tags()
tags.feed(index)
lead_form = next(attrs for tag, attrs in tags.items if (
    tag == "form" and attrs.get("id") == "lead-form"
))
success_panel = next(attrs for _, attrs in tags.items if (
    attrs.get("id") == "lead-success"
))
inputs = {
    attrs.get("name"): attrs for tag, attrs in tags.items if tag == "input"
}
assert lead_form["action"] == endpoint.group(1)
assert lead_form["method"] == "post"
assert "required" in inputs["name"]
assert success_panel["role"] == "status"
assert success_panel["aria-live"] == "polite"
assert "hidden" in success_panel
assert success_panel["tabindex"] == "-1"
assert "required" in inputs["email"]
assert inputs["privacy_consent"]["type"] == "checkbox"
assert "required" in inputs["privacy_consent"]
assert inputs["intent"] == {"type": "hidden", "name": "intent", "value": "project"}
assert "preferred_time" not in inputs
assert inputs["website"]["tabindex"] == "-1"
assert not any(attrs.get("data-lead-intent") == "booking" for _, attrs in tags.items)
assert 'href="privacy.html"' in index
assert '<meta name="robots" content="noindex, nofollow">' in index
assert "ProofFirst Studio" in index
assert "Melvin AI Web & Advertising Agency" not in index
assert all(value not in index for value in ("30 分钟", "预约", "booking"))
assert all(value not in index for value in (
    "Day085 Final Validation Agency", "example.com", "测试市场",
))
assert all(value in index for value in (
    "提交你的服务、目标市场和当前问题",
    "准备进入马来西亚市场",
    "告诉我们你的服务、目标市场和当前问题",
    '<link rel="icon" href="data:,">',
))
assert "新马来西亚" not in index
assert "/api/leads" not in script
assert '"Accept": "application/json"' in script
assert all(name in script for name in (
    "utm_source", "utm_medium", "utm_campaign", "source_workflow_id",
))
assert "booking" not in script
assert "preferred_time" not in script
assert "if (payload.website) return;" in script
assert 'if (!response.ok) throw new Error("submit failed");' in script
assert "AbortSignal.timeout(10000)" in script
assert all(value not in script for value in (
    "postMessage", "window.parent", 'addEventListener("message"',
))
assert all(value in privacy for value in (
    "Notis Privasi", "Privacy Notice", "个人资料私隐说明",
    "Formspree", "Vercel", "30 days", "30 hari",
    "Data controller", "Pengawal data", "资料控制者",
    "ProofFirst Studio",
    "membaca parameter UTM daripada URL secara automatik dan menambahkan pengecam aliran kerja tetap",
    "read UTM parameters from the URL automatically and add a fixed workflow identifier",
    "自动读取网址中的 UTM 参数，并附加固定工作流标识",
    '<meta name="robots" content="noindex, nofollow">',
))
assert "Melvin AI Web & Advertising Agency" not in privacy
assert all(value not in privacy for value in (
    "preferred call time", "masa panggilan pilihan", "偏好通话时间",
    "arrange a call", "mengatur panggilan", "安排通话",
))
privacy_tags = Tags()
privacy_tags.feed(privacy)
privacy_form = next(attrs for tag, attrs in privacy_tags.items if (
    tag == "form" and attrs.get("id") == "privacy-request"
))
privacy_inputs = {
    attrs.get("name"): attrs
    for tag, attrs in privacy_tags.items
    if tag in {"input", "textarea"}
}
assert privacy_form["action"] == endpoint.group(1)
assert privacy_form["method"] == "post"
assert privacy_inputs["intent"]["value"] == "privacy_request"
assert "required" in privacy_inputs["email"]
assert "required" in privacy_inputs["message"]
assert "privacy_consent" not in privacy_inputs
assert "7 calendar days" in privacy and "7 hari kalendar" in privacy
headers = str(config["headers"])
assert "connect-src 'self' https://formspree.io" in headers
assert "frame-ancestors 'none'" in headers
assert "X-Content-Type-Options" in headers
assert "X-Robots-Tag" in headers and "noindex, nofollow" in headers
assert "background:#b44727;color:#fff" in styles
assert (SITE / "robots.txt").read_text(encoding="utf-8") == (
    "User-agent: *\nDisallow: /\n"
)

browser_test = r'''
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
let submitHandler;
const status = { textContent: "", dataset: {} };
const submit = { disabled: false };
const success = { hidden: true, focused: false, focus() { this.focused = true; } };
const form = {
  hidden: false,
  querySelector(selector) { return selector === '[role="status"]' ? status : submit; },
  addEventListener(name, handler) { if (name === "submit") submitHandler = handler; },
  reportValidity() { return true; },
  reset() {},
};
class TestFormData {
  [Symbol.iterator]() { return [["name", "Test"], ["email", "test@example.com"], ["website", ""]][Symbol.iterator](); }
}
vm.runInNewContext(fs.readFileSync("public_site/script.js", "utf8"), {
  document: { getElementById(id) { return id === "lead-form" ? form : success; } },
  FormData: TestFormData,
  URLSearchParams,
  location: { search: "" },
  AbortSignal,
  fetch: async () => ({ ok: true }),
});
(async () => {
  await submitHandler({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(success.hidden, false);
  assert.equal(success.focused, true);
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
result = subprocess.run(
    ["node", "-e", browser_test], cwd=SITE.parent,
    capture_output=True, text=True, check=False,
)
assert result.returncode == 0, result.stderr

print("Public-site tests passed.")
