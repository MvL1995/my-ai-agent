import os
import tempfile

import memory


original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(
        temp_dir,
        "test_memory.db"
    )

    try:
        memory.init_memory_db()

        sensitive_result = memory.remember_memory(
            "preference",
            "API Key: sk-test-not-real"
        )

        assert sensitive_result.startswith(
            "拒绝保存："
        )
        assert memory.get_memory(
            "conversation",
            "preference"
        ) is None

        normal_result = memory.remember_memory(
            "preference",
            "我喜欢简洁的中文回答"
        )

        assert normal_result.startswith("已保存")
        assert memory.get_memory(
            "conversation",
            "preference"
        ) == "我喜欢简洁的中文回答"
    finally:
        memory.DB_PATH = original_db_path

print("Memory-write-security tests passed.")