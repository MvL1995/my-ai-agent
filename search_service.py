from dataclasses import dataclass

from agents import Runner

import memory

from search_routing import build_search_request


RESEARCH_RESULT_LABELS = (
    "【事实】",
    "【事实｜单一来源】",
    "【推断】",
)


@dataclass
class ResearchReport:
    verified_facts: str
    single_source_facts: str
    inferences: str


def render_research_report(report):
    return (
        f"【事实】\n{report.verified_facts}\n\n"
        f"【事实｜单一来源】\n{report.single_source_facts}\n\n"
        f"【推断】\n{report.inferences}"
    )


def run_agent_search(search_agent, request):
    result = Runner.run_sync(
        search_agent,
        request
    )
    return render_research_report(result.final_output)


def is_valid_search_result(message):
    return (
        isinstance(message, str)
        and bool(message.strip())
        and (
            "http://" in message
            or "https://" in message
        )
        and all(
            label in message
            for label in RESEARCH_RESULT_LABELS
        )
    )


def execute_search(
    search_agent,
    query,
    run_search=None,
    cache=None,
):
    if memory.contains_sensitive_memory(query):
        memory.record_memory_event(
            "search",
            "web",
            "rejected_sensitive"
        )

        return {
            "status": "rejected_sensitive",
            "message": (
                "拒绝搜索：检测到密码、"
                "API Key、Token 或密钥。"
            ),
        }

    if cache is not None:
        message = cache.get(query)

        if (
            message is not None
            and is_valid_search_result(message)
        ):
            memory.record_memory_event(
                "search",
                "web",
                "cache_hit"
            )
            return {
                "status": "completed",
                "message": message,
            }

    if run_search is None:
        run_search = run_agent_search

    request = build_search_request(query)

    for attempt in range(2):
        try:
            message = run_search(
                search_agent,
                request
            )
        except Exception:
            if attempt == 0:
                memory.record_memory_event(
                    "search",
                    "web",
                    "retrying"
                )
                continue

            memory.record_memory_event(
                "search",
                "web",
                "failed"
            )

            return {
                "status": "failed",
                "message": "搜索暂时失败，请稍后重试。",
            }

        if not is_valid_search_result(message):
            if attempt == 0:
                memory.record_memory_event(
                    "search",
                    "web",
                    "retrying_invalid"
                )
                request += (
                    "\n\n上一次结果缺少研究标签或有效来源。"
                    "请重写，并完整使用【事实】、"
                    "【事实｜单一来源】和【推断】；"
                    "某类没有内容时标注为无。"
                )
                continue

            memory.record_memory_event(
                "search",
                "web",
                "failed_invalid"
            )

            return {
                "status": "failed_invalid",
                "message": (
                    "搜索结果缺少有效来源或研究标签，"
                    "请稍后重试。"
                ),
            }

        memory.record_memory_event(
            "search",
            "web",
            "completed"
        )

        if cache is not None:
            cache.set(query, message)

        return {
            "status": "completed",
            "message": message,
        }
