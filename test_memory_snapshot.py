import os
import tempfile

import memory


snapshot_reader = getattr(
    memory,
    "get_memory_snapshot",
    None
)

assert snapshot_reader is not None, (
    "get_memory_snapshot() 尚未实现"
)

original_db_path = memory.DB_PATH

with tempfile.TemporaryDirectory() as temp_dir:
    memory.DB_PATH = os.path.join(
        temp_dir,
        "test_memory.db"
    )

    try:
        memory.init_memory_db()
        memory.save_memory(
            "conversation",
            "preference",
            "第一版偏好"
        )
        memory.save_memory(
            "conversation",
            "fact",
            "我目前在马来西亚"
        )

        first_snapshot = snapshot_reader()

        assert first_snapshot == {
            "important_memory": None,
            "preference": "第一版偏好",
            "goal": None,
            "fact": "我目前在马来西亚",
        }

        memory.save_memory(
            "conversation",
            "preference",
            "第二版偏好"
        )

        second_snapshot = snapshot_reader()

        assert second_snapshot["preference"] == "第二版偏好"
        assert first_snapshot["preference"] == "第一版偏好"
    finally:
        memory.DB_PATH = original_db_path

print("Memory-snapshot tests passed.")