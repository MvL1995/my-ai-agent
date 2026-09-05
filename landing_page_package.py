import json
from dataclasses import dataclass


REQUIRED_FILES = (
    "index.html",
    "styles.css",
    "script.js",
)


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
