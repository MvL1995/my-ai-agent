import os
import tempfile

import memory


remember_memory = getattr(memory, "remember_memory", None)
read_memories = getattr(memory, "read_memories", None)

assert remember_memory is not None, "remember_memory() 尚未实现"
assert read_memories is not None, "read_memories() 尚未实现"

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()

        assert remember_memory(
            "preference", "简洁中文"
        ) == "已保存 preference 长期记忆。"

        assert memory.get_memory(
            "conversation", "preference"
        ) == "简洁中文"

        summary = read_memories()
        assert "偏好: 简洁中文" in summary

        assert remember_memory(
            "invalid", "测试"
        ) == "不支持的记忆类型。"

        assert remember_memory(
            "goal", "   "
        ) == "记忆内容不能为空。"
    finally:
        memory.DB_PATH = original_db_path

print("Memory-tool tests passed.")