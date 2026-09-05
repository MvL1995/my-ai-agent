import os
import tempfile

import memory
from search_service import execute_search


original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()

        direct_calls = []

        def successful_search(agent, request):
            direct_calls.append((agent, request))
            return (
                "【事实】吉隆坡天气晴朗："
                "https://example.com/weather\n"
                "【事实｜单一来源】无\n"
                "【推断】适合外出。"
            )

        direct_result = execute_search(
            object(),
            "吉隆坡天气",
            run_search=successful_search,
        )

        assert direct_result == {
            "status": "completed",
            "message": (
                "【事实】吉隆坡天气晴朗："
                "https://example.com/weather\n"
                "【事实｜单一来源】无\n"
                "【推断】适合外出。"
            ),
        }
        assert len(direct_calls) == 1
        assert "吉隆坡天气" in direct_calls[0][1]

        def must_not_search(agent, request):
            raise AssertionError("敏感内容不应发送到搜索服务")

        sensitive_result = execute_search(
            object(),
            "API Key: sk-test-not-real",
            run_search=must_not_search,
        )

        assert sensitive_result == {
            "status": "rejected_sensitive",
            "message": "拒绝搜索：检测到密码、API Key、Token 或密钥。",
        }

        retry_calls = []

        def succeeds_on_second_attempt(agent, request):
            retry_calls.append((agent, request))

            if len(retry_calls) == 1:
                raise RuntimeError("temporary failure")

            return (
                "【事实】重试后成功：https://example.com/retry\n"
                "【事实｜单一来源】无\n"
                "【推断】结果可用。"
            )

        retry_result = execute_search(
            object(),
            "马来西亚天气",
            run_search=succeeds_on_second_attempt,
        )

        assert retry_result == {
            "status": "completed",
            "message": (
                "【事实】重试后成功：https://example.com/retry\n"
                "【事实｜单一来源】无\n"
                "【推断】结果可用。"
            ),
        }
        assert len(retry_calls) == 2

        failure_calls = []

        def always_fails(agent, request):
            failure_calls.append((agent, request))
            raise RuntimeError("temporary failure")

        failure_result = execute_search(
            object(),
            "持续失败测试",
            run_search=always_fails,
        )

        assert failure_result == {
            "status": "failed",
            "message": "搜索暂时失败，请稍后重试。",
        }
        assert len(failure_calls) == 2

        events = memory.get_memory_audit(limit=6)

        assert [event["status"] for event in events] == [
            "failed",
            "retrying",
            "completed",
            "retrying",
            "rejected_sensitive",
            "completed",
        ]

        assert all(event["action"] == "search" for event in events)
        assert all(event["memory_type"] == "web" for event in events)

        audit_text = str(events)
        assert "sk-test-not-real" not in audit_text
        assert "马来西亚天气" not in audit_text
        assert "持续失败测试" not in audit_text

    finally:
        memory.DB_PATH = original_db_path


print("Search-service retry tests passed.")
