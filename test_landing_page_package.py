import importlib.util
import json


module_spec = importlib.util.find_spec("landing_page_package")
assert module_spec is not None, "landing_page_package.py 尚未实现"

from landing_page_package import (
    LandingPagePackage,
    LEAD_CAPTURE_SCRIPT,
    validate_lead_capture_package,
    parse_landing_page_package,
)


files = {
    "index.html": "<main>Hello</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
package = parse_landing_page_package(json.dumps(files))

assert isinstance(package, LandingPagePackage)
lead_files = {
    "index.html": (
        '<form id="lead-form">'
        '<input name="name" required>'
        '<input name="email" type="email" required>'
        '<input name="company"><select name="intent" required>'
        '<option value="project"></option>'
        '<option value="booking"></option></select>'
        '<input name="preferred_time" type="datetime-local">'
        '<textarea name="message"></textarea>'
        '<div class="trap"><input name="website"></div>'
        '<button type="submit">Send</button>'
        '<p role="status" aria-live="polite"></p></form>'
        '<a data-lead-intent="booking" href="#lead-form">Book</a>'
        '<script src="script.js"></script>'
    ),
    "styles.css": ".trap { position: absolute; left: -9999px; }",
    "script.js": "generated script is replaced",
}
validated = validate_lead_capture_package(
    parse_landing_page_package(json.dumps(lead_files))
)
assert validated.files["script.js"] == LEAD_CAPTURE_SCRIPT
input_honeypot_files = {
    **lead_files,
    "index.html": lead_files["index.html"].replace(
        '<div class="trap"><input name="website"></div>',
        '<input class="honeypot" name="website">',
    ),
    "styles.css": ".honeypot { position: absolute; left: -9999px; }",
}
validate_lead_capture_package(parse_landing_page_package(json.dumps(input_honeypot_files)))

for marker in (
    'id="lead-form"',
    'name="preferred_time"',
    'value="booking"',
    'data-lead-intent="booking"',
    'src="script.js"',
):
    broken = {
        **lead_files,
        "index.html": lead_files["index.html"].replace(marker, "missing"),
    }
    try:
        validate_lead_capture_package(
            parse_landing_page_package(json.dumps(broken))
        )
    except ValueError as error:
        assert "缺少线索采集协议" in str(error)
    else:
        raise AssertionError(f"缺少 {marker} 必须被拒绝")

for broken in (
    {**lead_files, "index.html": lead_files["index.html"].replace('name="name" required', 'name="name"')},
    {**lead_files, "index.html": lead_files["index.html"].replace('value="booking"></option>', 'value="booking"></option><option value="other">Other</option>')},
    {**lead_files, "index.html": lead_files["index.html"].replace('type="datetime-local"', 'type="text"')},
    {**lead_files, "index.html": lead_files["index.html"].replace('type="submit"', 'type="button"')},
    {**lead_files, "index.html": lead_files["index.html"].replace('role="status"', 'role="note"')},
    {**lead_files, "index.html": lead_files["index.html"].replace('src="script.js"', 'src="https://example.com/evil.js"')},
    {**lead_files, "index.html": lead_files["index.html"].replace('</form>', '</form><script>alert(1)</script>')},
):
    try:
        validate_lead_capture_package(parse_landing_page_package(json.dumps(broken)))
    except ValueError as error:
        assert "缺少线索采集协议" in str(error)
    else:
        raise AssertionError("无效线索采集语义必须被拒绝")

for marker in (
    "lead-submit",
    "lead-result",
    "/api/leads",
    "response.ok",
    "event.source !== window.parent",
):
    assert marker in LEAD_CAPTURE_SCRIPT
assert LEAD_CAPTURE_SCRIPT.count("lead-submit") == 1
assert LEAD_CAPTURE_SCRIPT.count("/api/leads") == 1

assert package.files == files

invalid_outputs = (
    42,
    "not json",
    "[]",
    json.dumps({
        "index.html": "<main>Hello</main>",
        "styles.css": "main {}",
    }),
    json.dumps({**files, "README.md": "extra"}),
    json.dumps({**files, "script.js": 42}),
    json.dumps({**files, "index.html": " "}),
    json.dumps({**files, "styles.css": " "}),
)

for raw_output in invalid_outputs:
    try:
        parse_landing_page_package(raw_output)
    except ValueError:
        pass
    else:
        raise AssertionError(
            f"无效 Coding 输出必须被拒绝：{raw_output}"
        )

print("Landing-page-package tests passed.")
