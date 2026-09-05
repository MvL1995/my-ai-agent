import builtins
import os
import runpy
import tempfile
from pathlib import Path

import memory
import search_service
from search_cache import SearchCache


project_directory = Path(__file__).resolve().parent
original_input = builtins.input
original_db_path = memory.DB_PATH
original_execute_search = search_service.execute_search
original_working_directory = Path.cwd()
captured = {}


def fake_execute_search(
    search_agent,
    query,
    cache=None,
):
    captured["cache"] = cache
    return {
        "status": "failed",
        "message": "测试搜索已结束。",
    }


with tempfile.TemporaryDirectory(
    ignore_cleanup_errors=True
) as temp_dir:
    try:
        os.chdir(temp_dir)
        memory.DB_PATH = str(
            Path(temp_dir) / "test_memory.db"
        )
        search_service.execute_search = fake_execute_search

        user_inputs = iter([
            "搜索：缓存接线测试",
            "exit",
        ])
        builtins.input = lambda prompt="": next(user_inputs)

        namespace = runpy.run_path(
            str(project_directory / "main.py"),
            run_name="day024_main_test",
        )
        namespace["run_cli"]()

        assert isinstance(
            captured.get("cache"),
            SearchCache,
        )
        assert captured["cache"] is namespace["search_cache"]
    finally:
        builtins.input = original_input
        memory.DB_PATH = original_db_path
        search_service.execute_search = original_execute_search
        os.chdir(original_working_directory)


print("Main-search-cache tests passed.")
