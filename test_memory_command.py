import os
import tempfile

import memory


parser = getattr(memory, "extract_memory_command", None)

assert parser is not None, "extract_memory_command() 尚未实现"

cases = [
    ("记住偏好：我喜欢中文", ("preference", "我喜欢中文")),
    ("记住目标：完成 AI Agent", ("goal", "完成 AI Agent")),
    ("记住事实：我住在新加坡", ("fact", "我住在新加坡")),
    ("记住：普通重要信息", ("important_memory", "普通重要信息")),
]

for user_input, expected in cases:
    assert parser(user_input) == expected

assert parser("你好") is None

delete_memory = getattr(memory, "delete_memory", None)

assert delete_memory is not None, "delete_memory() 尚未实现"

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(temp_dir, "test_memory.db")

    try:
        memory.init_memory_db()
        memory.save_memory("conversation", "preference", "简洁中文")

        assert memory.get_memory(
            "conversation", "preference"
        ) == "简洁中文"

        assert delete_memory(
            "conversation", "preference"
        ) is True

        assert memory.get_memory(
            "conversation", "preference"
        ) is None

        assert delete_memory(
            "conversation", "preference"
        ) is False
    finally:
        memory.DB_PATH = original_db_path

print("Memory-management tests passed.")