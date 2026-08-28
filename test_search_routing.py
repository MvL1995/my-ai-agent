import importlib
import importlib.util

module_spec = importlib.util.find_spec("search_routing")
assert module_spec is not None, "search_routing.py 尚未实现"

search_routing = importlib.import_module("search_routing")

extract_search_query = getattr(
    search_routing,
    "extract_search_query",
    None
)
build_search_request = getattr(
    search_routing,
    "build_search_request",
    None
)

assert extract_search_query is not None
assert build_search_request is not None

assert extract_search_query("你好") is None
assert extract_search_query("请联网搜索天气") is None
assert extract_search_query("搜索： 吉隆坡天气 ") == "吉隆坡天气"
assert extract_search_query("搜索：") == ""

request = build_search_request(
    "吉隆坡天气",
    current_date="2026-08-28"
)

assert request == (
    "当前本地日期：2026-08-28\n"
    "请使用网页搜索回答，并在答案中列出来源链接：吉隆坡天气"
)

print("Search-routing tests passed.")