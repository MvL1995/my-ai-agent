import importlib.util
import os
import tempfile

import memory


module_spec = importlib.util.find_spec("search_cache")
assert module_spec is not None, "search_cache.py 尚未实现"

from search_cache import SearchCache
from search_service import execute_search


class ManualClock:
    def __init__(self, value=1000.0):
        self.value = value

    def __call__(self):
        return self.value


original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()

        clock = ManualClock()
        cache = SearchCache(
            ttl_seconds=300,
            clock=clock,
        )
        search_calls = []

        def successful_search(agent, request):
            search_calls.append(request)
            return (
                "吉隆坡天气晴朗："
                f"https://example.com/weather/{len(search_calls)}"
            )

        first_result = execute_search(
            object(),
            "  吉隆坡天气  ",
            run_search=successful_search,
            cache=cache,
        )
        second_result = execute_search(
            object(),
            "吉隆坡天气",
            run_search=successful_search,
            cache=cache,
        )

        assert first_result == second_result
        assert len(search_calls) == 1

        events = memory.get_memory_audit(limit=2)
        assert [event["status"] for event in events] == [
            "cache_hit",
            "completed",
        ]

        clock.value += 301

        expired_result = execute_search(
            object(),
            "吉隆坡天气",
            run_search=successful_search,
            cache=cache,
        )

        assert len(search_calls) == 2
        assert expired_result == {
            "status": "completed",
            "message": (
                "吉隆坡天气晴朗："
                "https://example.com/weather/2"
            ),
        }

        invalid_cache = SearchCache(
            ttl_seconds=300,
            clock=clock,
        )
        invalid_calls = []

        def invalid_search(agent, request):
            invalid_calls.append(request)
            return "没有来源链接"

        first_invalid = execute_search(
            object(),
            "无效搜索",
            run_search=invalid_search,
            cache=invalid_cache,
        )
        second_invalid = execute_search(
            object(),
            "无效搜索",
            run_search=invalid_search,
            cache=invalid_cache,
        )

        assert first_invalid["status"] == "failed_invalid"
        assert second_invalid["status"] == "failed_invalid"
        assert len(invalid_calls) == 4

    finally:
        memory.DB_PATH = original_db_path


print("Search-cache tests passed.")
