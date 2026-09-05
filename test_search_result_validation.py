import os
import tempfile

import memory
import search_service
from search_service import execute_search


ResearchReport = getattr(search_service, "ResearchReport", None)
render_research_report = getattr(
    search_service,
    "render_research_report",
    None,
)

assert ResearchReport is not None, "ResearchReport 尚未实现"
assert render_research_report is not None, "研究结果渲染尚未实现"

structured_message = render_research_report(
    ResearchReport(
        verified_facts="市场数据：https://example.com/official",
        single_source_facts="单一来源数据：https://example.com/source",
        inferences="建议先验证一个垂直行业。",
    )
)

assert structured_message == (
    "【事实】\n市场数据：https://example.com/official\n\n"
    "【事实｜单一来源】\n单一来源数据：https://example.com/source\n\n"
    "【推断】\n建议先验证一个垂直行业。"
)

original_run_sync = search_service.Runner.run_sync


class StructuredResult:
    final_output = ResearchReport(
        verified_facts="市场数据：https://example.com/official",
        single_source_facts="无",
        inferences="建议先验证一个垂直行业。",
    )


try:
    search_service.Runner.run_sync = lambda agent, request: StructuredResult()
    assert search_service.run_agent_search(object(), "市场机会") == (
        "【事实】\n市场数据：https://example.com/official\n\n"
        "【事实｜单一来源】\n无\n\n"
        "【推断】\n建议先验证一个垂直行业。"
    )
finally:
    search_service.Runner.run_sync = original_run_sync


original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()

        retry_calls = []

        def invalid_then_valid(agent, request):
            retry_calls.append(request)

            if len(retry_calls) == 1:
                return "天气晴朗，但没有来源"

            return (
                "【事实】天气晴朗：https://example.com/weather\n"
                "【事实｜单一来源】无\n"
                "【推断】适合外出。"
            )

        retry_result = execute_search(
            object(),
            "吉隆坡天气",
            run_search=invalid_then_valid,
        )

        assert retry_result == {
            "status": "completed",
            "message": (
                "【事实】天气晴朗：https://example.com/weather\n"
                "【事实｜单一来源】无\n"
                "【推断】适合外出。"
            ),
        }
        assert len(retry_calls) == 2

        label_retry_calls = []

        def unlabeled_then_labeled(agent, request):
            label_retry_calls.append(request)

            if len(label_retry_calls) == 1:
                return "市场有机会：https://example.com/market"

            return (
                "【事实】市场有机会：https://example.com/market\n"
                "【事实｜单一来源】无\n"
                "【推断】建议先做小规模验证。"
            )

        label_retry_result = execute_search(
            object(),
            "市场机会",
            run_search=unlabeled_then_labeled,
        )

        assert label_retry_result == {
            "status": "completed",
            "message": (
                "【事实】市场有机会：https://example.com/market\n"
                "【事实｜单一来源】无\n"
                "【推断】建议先做小规模验证。"
            ),
        }
        assert len(label_retry_calls) == 2
        assert "上一次结果缺少研究标签" in label_retry_calls[1]

        invalid_calls = []

        def always_invalid(agent, request):
            invalid_calls.append(request)

            if len(invalid_calls) == 1:
                return ""

            return "仍然没有来源链接"

        invalid_result = execute_search(
            object(),
            "持续无效结果测试",
            run_search=always_invalid,
        )

        assert invalid_result == {
            "status": "failed_invalid",
            "message": (
                "搜索结果缺少有效来源或研究标签，"
                "请稍后重试。"
            ),
        }
        assert len(invalid_calls) == 2

        events = memory.get_memory_audit(limit=6)

        assert [event["status"] for event in events] == [
            "failed_invalid",
            "retrying_invalid",
            "completed",
            "retrying_invalid",
            "completed",
            "retrying_invalid",
        ]

        audit_text = str(events)
        assert "吉隆坡天气" not in audit_text
        assert "example.com" not in audit_text

    finally:
        memory.DB_PATH = original_db_path


print("Search-result validation tests passed.")
