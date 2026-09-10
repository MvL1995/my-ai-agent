import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.text = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.items.append((tag, attributes))
        if tag == "section":
            self.sections.append((attributes.get("id"), attributes.get("class", "")))

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


SITE = Path(__file__).parent / "client_sites" / "sean_lam"
required = {
    "index.html",
    "en.html",
    "styles.css",
    "tokens.css",
    "script.js",
    "assets/sean-lam.jpeg",
    ".hallmark/log.json",
}
assert all((SITE / path).is_file() for path in required)

index = (SITE / "index.html").read_text(encoding="utf-8")
english = (SITE / "en.html").read_text(encoding="utf-8")
styles = (SITE / "styles.css").read_text(encoding="utf-8")
tokens = (SITE / "tokens.css").read_text(encoding="utf-8")
tags = Tags()
tags.feed(index)
english_tags = Tags()
english_tags.feed(english)
page_text = " ".join(tags.text)
english_page_text = " ".join(english_tags.text)

assert '<html lang="zh-CN">' in index
assert '<html lang="en">' in english
assert "viewport-fit=cover" in index
compact_page_text = page_text.replace(" ", "")
assert all(value.replace(" ", "") in compact_page_text for value in (
    "生病时，收入也需要保障。",
    "如果半年至一年不能工作，你现在的储蓄够吗？",
    "Allianz Life Changer",
    "疾病保障 ≠ Medical Card",
    "已经有保险？先别急着买新的。",
    "Sean 是怎样帮你规划的？",
    "LAM KOK SIONG",
    "Agent ID 260196-5",
    "Kuala Lumpur",
    "不需要马上决定买什么。",
    "产品详情以 Allianz 官方文件及保单条款为准。",
    "疾病保障一定会赔吗？",
    "最终以正式保单条款及理赔审核为准。",
))
assert all(value not in index for value in (
    "保证赔付", "保证获赔", "最低保费", "限时优惠",
    "客户见证", "成功案例", "KUALA LUMPUR PEOPLE PROTECTION",
    "sean-hero-option-3.png", "不 hard sell", "Allianz Life Agent",
))
assert 'src="assets/sean-lam.jpeg"' in index
assert "allianz-logo" not in index.lower()
assert all(value in english_page_text for value in (
    "When illness interrupts work, your income still needs protection.",
    "If you could not work for six months to a year, would your savings be enough?",
    "Critical illness cover ≠ Medical Card",
    "Already insured? Check what you have before buying anything new.",
    "How does Sean help you plan?",
    "Product details are subject to Allianz official documents and policy terms.",
))
assert "Allianz Life Agent" not in english

section_names = [
    section_id or next((name for name in classes.split() if name != "editorial-section"), "")
    for section_id, classes in tags.sections
]
expected_order = [
    "hero", "problem", "calculator", "coverage", "policy-check", "about",
    "process", "audience", "questions", "faq", "final-cta",
]
assert [section_names.index(name) for name in expected_order] == sorted(
    section_names.index(name) for name in expected_order
)
english_section_names = [
    section_id or next((name for name in classes.split() if name != "editorial-section"), "")
    for section_id, classes in english_tags.sections
]
assert english_section_names == section_names

for parser, current_language in ((tags, "zh-CN"), (english_tags, "en")):
    language_links = {
        attrs.get("data-language"): attrs
        for tag, attrs in parser.items
        if tag == "a" and attrs.get("data-language")
    }
    assert set(language_links) == {"zh-CN", "en"}
    assert language_links[current_language].get("aria-current") == "page"

ids = {attrs.get("id") for _, attrs in tags.items if attrs.get("id")}
assert {
    "hero-title", "hero-summary", "hero-primary", "exposure-form",
    "exposure-result", "cashflow-required", "cashflow-gap",
    "calculator-whatsapp", "intent-whatsapp", "faq-more",
}.issubset(ids)

intent_buttons = {
    attrs.get("data-intent")
    for tag, attrs in tags.items
    if tag == "button" and attrs.get("data-intent")
}
assert intent_buttons == {"protection", "existing", "budget", "general"}

primary_sources = {
    attrs.get("data-whatsapp-source")
    for tag, attrs in tags.items
    if tag == "a" and attrs.get("data-cta-level") == "primary"
}
assert primary_sources == {"hero", "footer", "mobile_sticky"}

whatsapp_links = [
    attrs for tag, attrs in tags.items
    if tag == "a" and attrs.get("data-whatsapp-source")
]
assert {
    "header", "hero", "calculator", "existing_policy",
    "question_selector", "footer", "mobile_sticky",
}.issubset({attrs["data-whatsapp-source"] for attrs in whatsapp_links})
assert all(
    attrs.get("href", "").startswith("https://wa.me/60166396106?text=")
    for attrs in whatsapp_links
)

inputs = {
    attrs.get("name"): attrs
    for tag, attrs in tags.items
    if tag == "input" and attrs.get("name")
}
assert set(inputs) == {"essentials", "commitments", "months", "savings", "benefits"}
assert inputs["months"]["value"] == "36"
assert inputs["months"]["min"] == "36"
assert inputs["months"]["max"] == "120"
assert "RM 144,000" in page_text
assert all(inputs[name].get("inputmode") in {"numeric", "decimal"} for name in inputs)
english_inputs = {
    attrs.get("name"): attrs
    for tag, attrs in english_tags.items
    if tag == "input" and attrs.get("name")
}
assert english_inputs["months"]["value"] == "36"
assert english_inputs["months"]["min"] == "36"
assert english_inputs["months"]["max"] == "120"

faq_buttons = [
    attrs for tag, attrs in tags.items
    if tag == "button" and "faq-question" in attrs.get("class", "").split()
]
assert len(faq_buttons) == 8
assert all(attrs.get("aria-expanded") == "false" for attrs in faq_buttons)
assert all(attrs.get("data-faq-question") for attrs in faq_buttons)
faq_extra = [
    attrs for tag, attrs in tags.items
    if tag == "article" and "faq-extra" in attrs.get("class", "").split()
]
assert len(faq_extra) == 2
assert all("hidden" in attrs for attrs in faq_extra)

assert styles.startswith("/* Hallmark ·")
assert '@import url("tokens.css")' in styles
assert "overflow-x: clip" in styles
assert "position: fixed" in styles and ".mobile-sticky" in styles
assert "@media (min-width: 48rem)" in styles
assert "@media (min-width: 64rem)" in styles
assert "--color-accent-ink" in tokens
assert (SITE / "assets" / "sean-lam.jpeg").stat().st_size > 100_000

history = json.loads((SITE / ".hallmark" / "log.json").read_text(encoding="utf-8"))
assert history[0]["macrostructure"] == "Conversational FAQ"
assert history[0]["theme"] == "Atelier"

node_test = r'''
const assert = require("node:assert/strict");
global.window = {
  dataLayer: [],
  gtagCalls: [],
  fbqCalls: [],
  gtag(...args) { this.gtagCalls.push(args); },
  fbq(...args) { this.fbqCalls.push(args); },
};
const {
  calculateCashflow,
  buildWhatsAppUrl,
  getCampaignContent,
  getReachedScrollDepths,
  trackEvent,
} = require("./client_sites/sean_lam/script.js");

assert.deepEqual(calculateCashflow(2500, 1500, 6, 5000, 3000), {
  required: 24000,
  available: 8000,
  gap: 16000,
});
assert.deepEqual(calculateCashflow(-1, 100, 6, -20, "bad"), {
  required: 600,
  available: 0,
  gap: 600,
});
assert.deepEqual(calculateCashflow(1000, 500, 0, 200, 100), {
  required: 0,
  available: 300,
  gap: 0,
});

const calculatorUrl = decodeURIComponent(buildWhatsAppUrl("calculator", {
  months: 6,
  required: 24000,
  gap: 16000,
}));
assert.match(calculatorUrl, /6 个月/);
assert.match(calculatorUrl, /RM24,000/);
assert.match(calculatorUrl, /RM16,000/);
for (const intent of ["protection", "existing", "budget", "general"]) {
  assert.match(buildWhatsAppUrl(intent), /^https:\/\/wa\.me\/60166396106\?text=/);
}
assert.match(decodeURIComponent(buildWhatsAppUrl("existing")), /现有保障有没有缺口/);
assert.match(
  decodeURIComponent(buildWhatsAppUrl("protection", {}, "en")),
  /I'd like to understand critical illness cover/
);
assert.match(
  decodeURIComponent(buildWhatsAppUrl("calculator", {
    months: 120,
    required: 480000,
    gap: 400000,
  }, "en")),
  /unable to work for 120 months/
);

assert.equal(getCampaignContent("cashflow").title, "如果生病半年不能工作，你的现金流够吗？");
assert.equal(
  getCampaignContent("cashflow", "en").title,
  "If illness kept you from working for six months, would your cash flow hold up?"
);
assert.equal(getCampaignContent("cashflow").href, "#calculator");
assert.equal(getCampaignContent("medical-card").href, "#coverage");
assert.equal(getCampaignContent("unknown").href, null);
assert.deepEqual(getReachedScrollDepths(76, new Set([25])), [50, 75]);
assert.deepEqual(getReachedScrollDepths(100, new Set([25, 50, 75])), [100]);

trackEvent("faq_opened", { faq_question: "medical_card_vs_ci" });
assert.deepEqual(window.dataLayer[0], {
  event: "faq_opened",
  faq_question: "medical_card_vs_ci",
});
assert.deepEqual(window.gtagCalls[0], ["event", "faq_opened", { faq_question: "medical_card_vs_ci" }]);
assert.deepEqual(window.fbqCalls[0], ["trackCustom", "faq_opened", { faq_question: "medical_card_vs_ci" }]);
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
