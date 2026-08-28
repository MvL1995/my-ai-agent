import os
import tempfile

import memory
from search_service import execute_search


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

            return "天气晴朗：https://example.com/weather"

        retry_result = execute_search(
            object(),
            "吉隆坡天气",
            run_search=invalid_then_valid,
        )

        assert retry_result == {
            "status": "completed",
            "message": "天气晴朗：https://example.com/weather",
        }
        assert len(retry_calls) == 2

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
            "message": "搜索结果缺少有效来源，请稍后重试。",
        }
        assert len(invalid_calls) == 2

        events = memory.get_memory_audit(limit=4)

        assert [event["status"] for event in events] == [
            "failed_invalid",
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