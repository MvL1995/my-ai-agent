import os
import tempfile

import memory


forget_memory = getattr(memory, "forget_memory", None)

assert forget_memory is not None, "forget_memory() 尚未实现"

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()
        memory.save_memory(
            "conversation",
            "preference",
            "简洁中文"
        )

        assert forget_memory(
            "preference"
        ) == "已删除 preference 长期记忆。"

        assert memory.get_memory(
            "conversation",
            "preference"
        ) is None

        assert forget_memory(
            "preference"
        ) == "preference 记忆不存在。"

        assert forget_memory(
            "invalid"
        ) == "不支持的记忆类型。"
    finally:
        memory.DB_PATH = original_db_path

print("Forget-memory tests passed.")