import subprocess
from html.parser import HTMLParser
from pathlib import Path


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data.strip())


SITE = Path(__file__).parent / "client_sites" / "sean_lam"
required = {
    "index.html",
    "styles.css",
    "script.js",
    "assets/sean-lam.jpeg",
}
assert all((SITE / path).is_file() for path in required)

index = (SITE / "index.html").read_text(encoding="utf-8")
styles = (SITE / "styles.css").read_text(encoding="utf-8")
tags = Tags()
tags.feed(index)
page_text = "".join(tags.text)

assert '<html lang="zh-CN">' in index
assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in index
assert all(value in page_text for value in (
    "生病时，收入也需要保障。",
    "如果因为重大疾病暂时无法工作，你现在的储蓄能够撑多久？",
    "疾病保障 ≠ 医疗卡",
    "LAM KOK SIONG",
    "Agent ID 260196-5",
    "Kuala Lumpur",
    "先了解，不代表一定要购买。",
    "已经有保险？也可以先检查",
    "产品详情以 Allianz 官方文件及保单条款为准。",
))
assert all(value not in index for value in (
    "保证赔付", "保证获赔", "一定会赔", "最低保费", "限时优惠",
    "客户见证", "成功案例", "KUALA LUMPUR PEOPLE PROTECTION",
))
assert "Allianz" not in index or "Allianz Life Agent" in index
assert "allianz-logo" not in index.lower()

ids = {attrs.get("id") for _, attrs in tags.items if attrs.get("id")}
assert {
    "coverage", "policy-check", "about", "process", "calculator", "faq",
    "exposure-form", "exposure-result",
}.issubset(ids)

intent_buttons = {
    attrs.get("data-intent")
    for tag, attrs in tags.items
    if tag == "button" and attrs.get("data-intent")
}
assert intent_buttons == {"protection", "existing", "budget", "general"}

cta_intents = [
    attrs.get("data-whatsapp-intent")
    for tag, attrs in tags.items
    if tag == "a" and attrs.get("data-whatsapp-intent")
]
assert set(cta_intents) == {"protection", "budget", "general"}
assert all(
    attrs.get("href", "").startswith("https://wa.me/?text=")
    for tag, attrs in tags.items
    if tag == "a" and attrs.get("data-whatsapp-intent")
)

inputs = {
    attrs.get("name"): attrs
    for tag, attrs in tags.items
    if tag == "input" and attrs.get("name")
}
assert set(inputs) == {"essentials", "commitments", "months"}
assert inputs["months"]["value"] == "6"
assert inputs["months"]["min"] == "1"
assert inputs["months"]["max"] == "24"

faq_buttons = [
    attrs for tag, attrs in tags.items
    if tag == "button" and attrs.get("class") == "faq-question"
]
assert len(faq_buttons) == 8
assert all(attrs.get("aria-expanded") == "false" for attrs in faq_buttons)
assert all(attrs.get("aria-controls") in ids for attrs in faq_buttons)
faq_panels = [
    attrs for _, attrs in tags.items if attrs.get("class") == "faq-answer"
]
assert len(faq_panels) == 8
assert all("hidden" in attrs for attrs in faq_panels)

assert "@media (max-width: 760px)" in styles
assert "focus-visible" in styles
assert (SITE / "assets" / "sean-lam.jpeg").stat().st_size > 100_000

node_test = r'''
const assert = require("node:assert/strict");
const { calculateExposure, buildWhatsAppUrl } = require("./client_sites/sean_lam/script.js");

assert.equal(calculateExposure(2500, 1500, 6), 24000);
assert.equal(calculateExposure(-1, 100, 6), 600);
assert.equal(calculateExposure("bad", 100, 6), 600);
assert.equal(calculateExposure(1000, 500, 0), 0);

for (const intent of ["protection", "existing", "budget", "general"]) {
  assert.match(buildWhatsAppUrl(intent), /^https:\/\/wa\.me\/\?text=/);
}
assert.match(decodeURIComponent(buildWhatsAppUrl("existing")), /已经有保险/);
assert.match(decodeURIComponent(buildWhatsAppUrl("budget")), /预算/);
assert.match(decodeURIComponent(buildWhatsAppUrl("unknown")), /先了解/);
'''
result = subprocess.run(
    ["node", "-e", node_test],
    cwd=SITE.parent.parent,
    capture_output=True,
    text=True,
    check=False,
)
assert result.returncode == 0, result.stderr

print("Sean Lam site tests passed.")
