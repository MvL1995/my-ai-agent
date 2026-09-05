import importlib.util
import json


module_spec = importlib.util.find_spec("landing_page_package")
assert module_spec is not None, "landing_page_package.py 尚未实现"

from landing_page_package import (
    LandingPagePackage,
    parse_landing_page_package,
)


files = {
    "index.html": "<main>Hello</main>",
    "styles.css": "main { color: black; }",
    "script.js": "",
}
package = parse_landing_page_package(json.dumps(files))

assert isinstance(package, LandingPagePackage)
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
